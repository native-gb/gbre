# Repository and legal model

This is a conservative engineering policy, not legal advice. It is focused on
United States public distribution. Reverse engineering and trademark rules are
fact- and jurisdiction-specific.

## Three distinct repositories

For each game:

1. GBRE holds reusable analysis and comparison machinery.
2. `native-gb-<game>` holds the independently written native implementation and
   is the only C++ workspace.
3. `native-gb-<game>-re` holds the private semantic map, scenario database,
   game-specific oracle configuration, and reproducible research artifacts.

The split is about clean ownership, release auditing, and maintainability. A
private repository is not a legal safe harbor. Original ROMs, extracted
audiovisual assets, save states, and large memory dumps stay out of GitHub
regardless of visibility.

## Public material

Public GBRE and port repositories may contain independently written code,
schemas, algorithms, annotations expressed as facts, hashes, build scripts, and
documentation. They should not contain copied ROM bytes, official art or audio,
wholesale disassembly source, or packaging that suggests an official product.

The public port reads a compatible ROM supplied locally by the user, verifies
its identity, and creates only ignored local caches. An emulator may be used as
a development oracle but is not a dependency of the shipped native game.

## Names

Use a game's name only as ordinary text needed to identify compatibility. Do
not use official logos, trade dress, or claims of endorsement. Put a prominent
unofficial-project disclaimer in the README, notices, and release description.
Whether a particular name or presentation is lawful depends on the actual facts;
repository naming is not a guarantee.

## Reverse engineering label

Describing GBRE as reverse-engineering software is accurate and not itself an
admission of infringement. United States law expressly uses the heading
“Reverse Engineering” in 17 U.S.C. §1201(f). That provision is limited and
conditional, so project descriptions should state the concrete purpose:
research, compatibility, and interoperability with lawfully obtained software.

## References

- [17 U.S.C. §102](https://www.copyright.gov/title17/92chap1.html#102)
- [17 U.S.C. §1201(f)](https://www.copyright.gov/title17/92chap12.html#1201)
- [Copyright Office Circular 61](https://www.copyright.gov/circs/circ61.pdf)
- [New Kids on the Block v. News America](https://law.justia.com/cases/federal/appellate-courts/F2/971/302/72076/)
- [GitHub DMCA Takedown Policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy)
- [GitHub content-removal policies](https://docs.github.com/en/site-policy/content-removal-policies/submitting-content-removal-requests)
