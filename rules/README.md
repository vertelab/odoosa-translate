# Rules — Schema och användning

Strukturerade korrigeringsregler för svenska översättningar av Odoo SA-kärnmoduler.
Ersätter det gamla `odoo18-sv-translations.txt`. Ordlistan (`glossary.csv`) är den
version-agnostiska termbasen; reglerna är det operationella lagret.

## Filstruktur

```
rules/
├── core.yml          # Gemensam kärna — regler som gäller för flera utgåvor
├── odoo-18.yml       # Versionsspecifikt (18.0)
├── odoo-19.yml       # Versionsspecifikt (19.0)
└── README.md         # Detta dokument
```

## Term-struktur (YAML)

```yaml
terms:
  - id: verifikat            # unik identifierare
    glossary_ref: "account move"   # källa i glossary.csv (informativt)
    old: "Bokföringspost"     # huvudform (kortaste — appliceras sist)
    new: "Verifikat"          # mål för huvudformen
    variants:                 # ytterligare old→new-par (längsta först)
      - old: "Bokföringsposterna"
        new: "Verifikaten"
    modules: [account, base]  # modul-scop; "*" = alla moduler
    versions: [18, 19]        # utgåvor regeln gäller för
    only_if_msgid: '\b(Company|Companies)\b'  # villkor på msgid (regex)
    match: longest            # längsta-match-strategi
    note: "Klagomål 2026-08-13, sparv"  # revisionsspår / kommentar
```

## Semantik

- **Appliceras på `msgstr`** — aldrig på `msgid`.
- **Längsta match först**: av alla `old` (huvudform + varianter) inom modul-
  och versionscope vinner den längsta matchande strängen.
- **`only_if_msgid`**: regex som måste matcha msgid för att regeln ska
  appliceras (t.ex. Företag→Bolag endast när msgid innehåller Company/Companies —
  INTE Corporate/Business).
- **Versionsscop**: `versions: [18, 19]` = delad kärna. Per-version-filer
  (`odoo-<edition>.yml`) kan lägga till nya regler eller **överrida** en
  kärnregel med samma `id`.
- **Modulscop**: `modules: "*"` = alla moduler; lista = endast de modulerna.
- Reglerna verkar på alla fraser (även nya) → ny text med känd felterm
  korrigeras automatiskt.

## Lägga till / ändra en term (klagomålsregelverket)

**Enkla fall — använd `odoosa.py add-term` (du rör ALDRIG YAML):**

```bash
./odoosa.py add-term --module account --old "Bokföringspost" --new "Verifikat"
# valfritt: --note "klagomålsreferens"
```

Manuellt (avancerat):

1. Sök i `glossary.csv` — finns termen? Om inte: besluta term och lägg till.
2. Lägg till/ändra regel i `rules/core.yml` (eller `rules/odoo-<edition>.yml`
   om versionsspecifikt), med `note` = klagomålsreferens.
3. Kör `odoosa.py build` + regression (måste reproducera senaste snapshot).
4. Nästa veckosync (måndag 05:30) rullar ut ändringen automatiskt.

Flaggning av fraser (undanta från översättning + räknas inte som ny i loggen)
sker via `odoosa.py flag-term` — se `rules/flagged.yml` eller Driftsloggens
"📖 Don't make me think"-manual.
