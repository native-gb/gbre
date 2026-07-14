const fs = require('fs');
const path = require('path');
const vscode = require('vscode');

const referencePattern = /GBRE:\s*([A-Za-z0-9_.-]+)/g;
let reportPanel;
let databaseCache;
let reportSyncTimer;

function workspaceRoot() {
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!folder)
        throw new Error('GBRE requires an open workspace.');
    return folder.uri.fsPath;
}

function configuredPath(name) {
    let value = vscode.workspace.getConfiguration('gbre').get(name, '');
    if (!value)
        throw new Error(`Set gbre.${name} in workspace settings.`);
    value = value.replaceAll('${workspaceFolder}', workspaceRoot());
    return path.resolve(workspaceRoot(), value);
}

function parseCsv(text) {
    const records = [];
    let record = [], field = '', quoted = false;
    for (let index = 0; index < text.length; ++index) {
        const character = text[index];
        if (quoted) {
            if (character === '"' && text[index + 1] === '"') {
                field += '"';
                ++index;
            } else if (character === '"') {
                quoted = false;
            } else {
                field += character;
            }
        } else if (character === '"') {
            quoted = true;
        } else if (character === ',') {
            record.push(field);
            field = '';
        } else if (character === '\n') {
            record.push(field.replace(/\r$/, ''));
            records.push(record);
            record = [];
            field = '';
        } else {
            field += character;
        }
    }
    if (field || record.length) {
        record.push(field);
        records.push(record);
    }
    const headers = records.shift() || [];
    return records.filter(record => record.length === headers.length).map(record =>
        Object.fromEntries(headers.map((header, index) => [header, record[index]]))
    );
}

function loadDatabase() {
    const manifestPath = configuredPath('manifest');
    const romMapPath = configuredPath('romMap');
    const signature = `${manifestPath}:${fs.statSync(manifestPath).mtimeMs}:${romMapPath}:${fs.statSync(romMapPath).mtimeMs}`;
    if (databaseCache?.signature === signature)
        return databaseCache.database;
    const database = {
        manifestPath,
        manifest: JSON.parse(fs.readFileSync(manifestPath, 'utf8')),
        rows: parseCsv(fs.readFileSync(romMapPath, 'utf8')),
    };
    databaseCache = {signature, database};
    return database;
}

function queryAtEditor() {
    const editor = vscode.window.activeTextEditor;
    if (!editor)
        return '';
    const selection = editor.document.getText(editor.selection).trim();
    if (selection)
        return selection;
    const line = editor.document.lineAt(editor.selection.active.line).text;
    const match = [...line.matchAll(referencePattern)].find(item =>
        item.index <= editor.selection.active.character &&
        item.index + item[0].length >= editor.selection.active.character
    );
    if (match)
        return match[1];
    return editor.document.getText(editor.document.getWordRangeAtPosition(editor.selection.active));
}

function referenceAt(document, position) {
    const line = document.lineAt(position.line).text;
    return [...line.matchAll(referencePattern)].find(item =>
        item.index <= position.character &&
        item.index + item[0].length >= position.character
    )?.[1];
}

function parseAddress(query) {
    const match = query.trim().match(/^(?:0x|\$)?([0-9a-f]+)$/i);
    return match ? Number.parseInt(match[1], 16) : null;
}

function findRow(rows, query) {
    const address = parseAddress(query);
    if (address !== null)
        return rows.find(row => Number.parseInt(row.start, 16) <= address && address < Number.parseInt(row.end_exclusive, 16));
    const lowered = query.toLowerCase();
    return rows.find(row => row.unit_id.toLowerCase() === lowered || row.symbol.toLowerCase() === lowered)
        || rows.find(row => row.unit_id.toLowerCase().includes(lowered) || row.symbol.toLowerCase().includes(lowered));
}

function queryForEditorLocation(editor) {
    if (!editor)
        return '';
    const selected = editor.document.getText(editor.selection).trim();
    if (selected)
        return selected;
    const lineText = editor.document.lineAt(editor.selection.active.line).text;
    const directReference = [...lineText.matchAll(referencePattern)][0]?.[1];
    if (directReference)
        return directReference;

    try {
        const database = loadDatabase();
        const referenceRoot = configuredPath('referenceRoot');
        const relative = path.relative(referenceRoot, editor.document.uri.fsPath).split(path.sep).join('/');
        if (!relative.startsWith('../') && !path.isAbsolute(relative)) {
            const line = editor.selection.active.line + 1;
            const candidates = database.rows.filter(row => row.source_file === relative);
            const row = candidates.reduce((best, item) =>
                !best || Math.abs(Number(item.source_line) - line) < Math.abs(Number(best.source_line) - line)
                    ? item : best, undefined);
            if (row && Math.abs(Number(row.source_line) - line) <= 3)
                return row.unit_id || row.start;
        }

        const currentPath = path.resolve(editor.document.uri.fsPath);
        const currentLine = editor.selection.active.line + 1;
        let nearest;
        for (const unit of database.manifest.units) {
            for (const target of unit.native || []) {
                const repoRoot = path.dirname(path.dirname(database.manifestPath));
                const targetPath = path.resolve(repoRoot, target.path);
                if (targetPath !== currentPath)
                    continue;
                const anchorLine = editor.document.getText().split(/\r?\n/).findIndex(text => text.includes(target.anchor)) + 1;
                if (anchorLine > 0 && anchorLine <= currentLine && (!nearest || anchorLine > nearest.line))
                    nearest = {line: anchorLine, query: unit.id};
            }
        }
        if (nearest)
            return nearest.query;
    } catch (_) {
        // An editor outside the configured game has no live ROM selection.
    }
    return '';
}

async function resolveRow(query) {
    const database = loadDatabase();
    query ||= queryAtEditor();
    if (!query)
        query = await vscode.window.showInputBox({prompt: 'GBRE ID, assembly symbol, or ROM address'});
    if (!query)
        return {};
    const row = findRow(database.rows, query);
    if (!row)
        throw new Error(`No GBRE mapping matches ${query}.`);
    return {database, row};
}

async function showFile(filePath, line) {
    const document = await vscode.workspace.openTextDocument(filePath);
    const position = new vscode.Position(Math.max(0, line - 1), 0);
    await vscode.window.showTextDocument(document, {
        preview: true,
        selection: new vscode.Range(position, position),
    });
}

async function openAssembly(query) {
    const {row} = await resolveRow(query);
    if (!row)
        return;
    if (!row.source_file)
        throw new Error('This range has no assembly-source evidence yet.');
    await showFile(path.join(configuredPath('referenceRoot'), row.source_file), Number(row.source_line));
}

function unitFor(database, row) {
    return database.manifest.units.find(unit => unit.id === row.unit_id);
}

async function openNative(query) {
    const {database, row} = await resolveRow(query);
    if (!row)
        return;
    const unit = unitFor(database, row);
    if (!unit?.native?.length)
        throw new Error('This range has no native replacement yet.');
    const target = unit.native[0];
    const repoRoot = path.dirname(path.dirname(database.manifestPath));
    const targetPath = path.resolve(repoRoot, target.path);
    const lines = fs.readFileSync(targetPath, 'utf8').split(/\r?\n/);
    const line = Math.max(1, lines.findIndex(text => text.includes(target.anchor)) + 1);
    await showFile(targetPath, line);
}

async function openReport(query) {
    query ||= queryForEditorLocation(vscode.window.activeTextEditor);
    if (reportPanel) {
        reportPanel.reveal(vscode.ViewColumn.Beside);
        if (query)
            reportPanel.webview.postMessage({command: 'select', query});
        return;
    }

    reportPanel = vscode.window.createWebviewPanel(
        'gbreRomMap',
        'GBRE ROM Map',
        vscode.ViewColumn.Beside,
        {enableScripts: true, retainContextWhenHidden: true},
    );
    reportPanel.onDidDispose(() => reportPanel = undefined);
    reportPanel.webview.onDidReceiveMessage(async message => {
        if (message.command !== 'openFile')
            return;
        const decoded = decodeURI(message.href).replace(/^vscode:\/\/file/, '');
        const match = decoded.match(/^(.*):(\d+)$/);
        const filePath = match ? match[1] : decoded;
        const line = match ? Number(match[2]) : 1;
        await showFile(filePath, line);
    });

    const bridge = `<script>
const gbreVsCodeApi = acquireVsCodeApi();
window.addEventListener('message', event => {
    if (event.data.command === 'select')
        selectQuery(event.data.query);
});
document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="vscode://file"]');
    if (!link)
        return;
    event.preventDefault();
    gbreVsCodeApi.postMessage({command: 'openFile', href: link.href});
});
selectQuery(${JSON.stringify(query || '')});
</script>`;
    const report = fs.readFileSync(configuredPath('report'), 'utf8');
    reportPanel.webview.html = report.replace('</body>', `${bridge}</body>`);
}

async function gotoAddress() {
    const query = await vscode.window.showInputBox({prompt: 'ROM address', placeHolder: '0x2007'});
    if (query)
        await openAssembly(query);
}

function commandUri(command, argument) {
    return vscode.Uri.parse(`command:${command}?${encodeURIComponent(JSON.stringify([argument]))}`);
}

class ReferenceCodeLensProvider {
    provideCodeLenses(document) {
        const lenses = [];
        for (let line = 0; line < document.lineCount; ++line) {
            const text = document.lineAt(line).text;
            for (const match of text.matchAll(referencePattern)) {
                const range = new vscode.Range(line, match.index, line, match.index + match[0].length);
                lenses.push(new vscode.CodeLens(range, {title: '$(symbol-method) Assembly', command: 'gbre.openAssembly', arguments: [match[1]]}));
                lenses.push(new vscode.CodeLens(range, {title: '$(map) ROM map', command: 'gbre.openReport', arguments: [match[1]]}));
            }
        }

        try {
            const referenceRoot = configuredPath('referenceRoot');
            const relativePath = path.relative(referenceRoot, document.uri.fsPath).split(path.sep).join('/');
            if (relativePath.startsWith('../'))
                return lenses;
            const database = loadDatabase();
            const seen = new Set();
            for (const row of database.rows) {
                if (row.source_file !== relativePath || !row.unit_id || !row.native_location || seen.has(row.unit_id))
                    continue;
                seen.add(row.unit_id);
                const line = Math.max(0, Number(row.source_line) - 1);
                const range = new vscode.Range(line, 0, line, 0);
                lenses.push(new vscode.CodeLens(range, {
                    title: `$(code) Native · ${row.unit_id}`,
                    command: 'gbre.openNative',
                    arguments: [row.unit_id],
                }));
                lenses.push(new vscode.CodeLens(range, {
                    title: '$(map) ROM map',
                    command: 'gbre.openReport',
                    arguments: [row.unit_id],
                }));
            }
        } catch (_) {
            // A non-GBRE workspace simply has no assembly-side CodeLens.
        }
        return lenses;
    }
}

class ReferenceLinkProvider {
    provideDocumentLinks(document) {
        const links = [];
        for (let line = 0; line < document.lineCount; ++line) {
            const text = document.lineAt(line).text;
            for (const match of text.matchAll(referencePattern)) {
                const start = match.index + match[0].indexOf(match[1]);
                const range = new vscode.Range(line, start, line, start + match[1].length);
                links.push(new vscode.DocumentLink(range, commandUri('gbre.openAssembly', match[1])));
            }
        }
        return links;
    }
}

class ReferenceDefinitionProvider {
    provideDefinition(document, position) {
        const query = referenceAt(document, position);
        if (!query)
            return undefined;
        try {
            const database = loadDatabase();
            const row = findRow(database.rows, query);
            if (!row?.source_file)
                return undefined;
            const target = path.join(configuredPath('referenceRoot'), row.source_file);
            return new vscode.Location(
                vscode.Uri.file(target),
                new vscode.Position(Math.max(0, Number(row.source_line) - 1), 0),
            );
        } catch (_) {
            return undefined;
        }
    }
}

function guarded(callback) {
    return async (...args) => {
        try {
            await callback(...args);
        } catch (error) {
            vscode.window.showErrorMessage(`GBRE: ${error.message}`);
        }
    };
}

async function applyRgbdsLanguage(document) {
    if (document.uri.scheme !== 'file' || path.extname(document.uri.fsPath).toLowerCase() !== '.asm')
        return;
    try {
        const referenceRoot = configuredPath('referenceRoot');
        const relative = path.relative(referenceRoot, document.uri.fsPath);
        if (relative.startsWith('..') || path.isAbsolute(relative) || document.languageId === 'rgbds')
            return;
        await vscode.languages.setTextDocumentLanguage(document, 'rgbds');
    } catch (_) {
        // Other workspaces keep their existing assembly language selection.
    }
}

function scheduleReportSync(editor) {
    if (!reportPanel || !editor)
        return;
    clearTimeout(reportSyncTimer);
    reportSyncTimer = setTimeout(() => {
        const query = queryForEditorLocation(editor);
        if (query && reportPanel)
            reportPanel.webview.postMessage({command: 'select', query});
    }, 80);
}

function activate(context) {
    context.subscriptions.push(
        vscode.commands.registerCommand('gbre.openAssembly', guarded(openAssembly)),
        vscode.commands.registerCommand('gbre.openNative', guarded(openNative)),
        vscode.commands.registerCommand('gbre.openReport', guarded(openReport)),
        vscode.commands.registerCommand('gbre.gotoAddress', guarded(gotoAddress)),
        vscode.languages.registerCodeLensProvider({scheme: 'file'}, new ReferenceCodeLensProvider()),
        vscode.languages.registerDocumentLinkProvider({scheme: 'file'}, new ReferenceLinkProvider()),
        vscode.languages.registerDefinitionProvider({scheme: 'file'}, new ReferenceDefinitionProvider()),
        vscode.workspace.onDidOpenTextDocument(applyRgbdsLanguage),
        vscode.window.onDidChangeActiveTextEditor(scheduleReportSync),
        vscode.window.onDidChangeTextEditorSelection(event => scheduleReportSync(event.textEditor)),
    );
    for (const document of vscode.workspace.textDocuments)
        applyRgbdsLanguage(document);
}

function deactivate() {}

module.exports = {activate, deactivate, parseCsv, findRow};
