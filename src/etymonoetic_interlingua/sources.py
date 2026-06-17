from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from etymonoetic_interlingua.templates import slugify


WIKTIONARY_LICENSE = "CC BY-SA 4.0 and GFDL; see Wiktionary terms for details"


@dataclass(frozen=True)
class LexicalSource:
    id: str
    source_type: str
    citation: str
    url: str | None = None
    license: str | None = None
    accessed: str | None = None
    note: str | None = None

    def to_provenance(self) -> dict[str, str]:
        entry = {
            "id": self.id,
            "source_type": self.source_type,
            "citation": self.citation,
        }
        for key in ("url", "license", "accessed", "note"):
            value = getattr(self, key)
            if value:
                entry[key] = value
        return entry


def wiktionary_source(form: str, *, language: str = "en", accessed: str | None = None) -> LexicalSource:
    if language != "en":
        raise ValueError("Only English Wiktionary source URLs are supported in the MVP")

    normalized = slugify(form)
    access_date = accessed or date.today().isoformat()
    return LexicalSource(
        id=f"wiktionary-en-{normalized}",
        source_type="dictionary",
        citation=f'Wiktionary contributors, "{normalized}", Wiktionary, The Free Dictionary.',
        url=f"https://en.wiktionary.org/wiki/{normalized}",
        license=WIKTIONARY_LICENSE,
        accessed=access_date,
        note="Use as a cited lexical source; manually normalize claims into EI layers.",
    )
