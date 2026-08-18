# odoosa-translate

> Odoo SA Translation, Vertel Style — kontinuerlig, multi-utgåva svensk översättning
> av Odoo-kärnan, baserad på Odoo SAs officiella översättningar + vår terminologi.

Vi äger **bara avvikelser**: överlagringar levereras via Odoos native
**`i18n_extra`**-mekanism, så officiella `i18n/sv.po` lämnas orörda och vi
konvergerar automatiskt när Odoo SA antar våra begrepp.

- 📖 **Drift & kommandon**: [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- ✅ Aktiva utgåvor: **18.0**, **19.0** (20.0 config-driven när den släpps)

---

## Innehåll

- [Repository-struktur](#repository-struktur)
- [Ordlista & regler](#ordlista--regler)
- [Pipelinen](#pipelinen)
- [Veckoarbetsflöde](#veckoarbetsflöde)
- [Ny Odoo-utgåva](#ny-odoo-utgåva)
- [Klagomål på översättningen](#klagomål-på-översättningen)
- [Distribution](#distribution)
- [Säkerhet](#säkerhet)

## Repository-struktur

```
glossary.csv                  Termbas (source,target) — källa för begrepp
rules/
├── core.yml                  Delad regelkärna (versions: [18, 19])
├── odoo-18.yml               Versionsspecifikt (18.0)
├── odoo-19.yml               Versionsspecifikt (19.0)
└── README.md                 Schema-dokumentation
odoosa.py                     Pipeline: fetch → apply → merge → build → publish
build/odoo-<edition>/         Genererade artefakter
├── i18n_extra/<modul>/i18n_extra/sv.po  Våra överlagringar (deployas)
├── diff/<modul>/sv.po        Gransknings-diff
└── i18n/<modul>/sv.po        Officiella (orörda, ej publicerade)
reports/                      Veckorapporter
docs/OPERATIONS.md            Drift: kommandon, aktivering, felsökning
odoo-18-*-sv.po               Historiska snapshot (regressions-referens)
```

## Ordlista & regler

- **`glossary.csv`** — version-agnostisk termbas. Lägg till nya begrepp här.
- **`rules/core.yml`** — delad kärna: `versions: [18, 19]`, `modules: "*"` eller
  lista, `only_if_msgid` för kontextvillkor, `note` för klagomålsspår.
- **`rules/odoo-<edition>.yml`** — versionsspecifikt; samma `id` överridar kärnan.

Semantik: regler appliceras på **msgstr** (aldrig msgid), **längsta match först**,
`only_if_msgid` = regex mot msgid (t.ex. Företag→Bolag bara när msgid innehåller
`Company`/`Companies` — inte `Corporate`/`Business`).

**Översätt INTE:** utländska `l10n_*`-moduler (l10n_de, l10n_fr, l10n_pl,
l10n_cn …) — det är "tysk/polsk/kinesisk bokföring på svenska". Endast
`l10n_se` är relevant för Sverige.

**ENDAST Odoo SA-moduler (krav 2026-08-18):** detta system lägger bara
översättningar på Odoo SA-kärnan (`odoo/odoo`). Våra egna moduler, OCA och
annan tredje part hanteras av andra system och rörs ALDRIG. Två hårda skydd:
`odoosa.py validate_sa_only()` avbryter pipelinen om en icke-SA-modul hamnar
i bygget, och deploy-staten (`odoosa.deploy` + `odoo/19.sls`-hooken) vägrar
om i18n_extra-trädet innehåller en modul som inte finns i det officiella
`i18n/`-spegelträdet.

## Pipelinen

```bash
# Hela kedjan för en utgåva (eller alla)
./odoosa.py run --versions 18.0,19.0

# Enskilda steg
./odoosa.py fetch  --versions 18.0     # officiella sv.po → cache/
./odoosa.py apply  --versions 18.0     # regler → desired
./odoosa.py build  --versions 18.0     # i18n_extra + diff + rapport
./odoosa.py publish                    # commit + push till GitHub
./odoosa.py regression --versions 18.0 # jämför mot gamla snapshots
./odoosa.py check-edition 20.0         # verifiera i18n_extra (ny-utgåva)
```

Trevägs-mergen klassificerar varje fras:

| Användarfall | Förra | Nu | Vår vilja | Beslut |
|---|---|---|---|---|
| Översatt, fel begrepp | Bokföringspost | Bokföringspost | Verifikat | **Override** |
| Konvergerat 🎉 | Bokföringspost | Verifikat | Verifikat | Släpp vår post |
| Konflikt ⚠️ | Bokföringspost | Bokföringspost (rad) | Verifikat | Behåll + flagga |
| Oöversatt, vi har term | (tom) | (tom) | Verifikat | Fyll via regel |
| Oöversatt, ingen term | (tom) | (tom) | (—) | Lämna + flagga |
| Ny, redan rätt | — | Verifikat | — | Ingen åtgärd |
| Ny, fel begrepp | — | Bokföringspost | Verifikat | Korrigera |
| Borttagen | Bokföringspost | — | Verifikat | Städa bort |

## Veckoarbetsflöde

Weblate trycker översättningar till Odoo SA-filerna **på söndag** → måndagens
filer är "sanningen". En dedikerad **arbetsminion** kör måndag 05:30:

```
run (fetch → apply → merge → build)
  → publish (GitHub)
  → sync-master (cp.push till salt-mastern)
  → Driftslogg (ledningssystem.vertel.se/saltstack/log)
```

Salt-mastern distribuerar (gated) till odoo-minioner i **`production` (kunder),
`dev` och `test`** per `odoo_version`-grain — **aldrig `infra`** (krav 2026-08-18,
se [`docs/OPERATIONS.md`](docs/OPERATIONS.md) avsnitt 3) — och samkör med
varannan-vecka-uppdateringen (7:e/21:e). Se [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
för aktiveringsproceduren.

## Ny Odoo-utgåva

1. **Verifiera `i18n_extra`** — `./odoosa.py check-edition 20.0` (mekanismen
   måste finnas i `get_po_paths`).
2. **Lägg till lane** — `--versions 18.0,19.0,20.0` + `rules/odoo-20.yml`
   (ärv kärnan, lägg versionsspecifikt).
3. **Baseline-build** — första körningen klassar allt som "ny" → initial
   i18n_extra (official + regler).
4. **Granska rapport** — nya/omdöpta moduler, strängskillnader.
5. **Deploy-state** — `odoo/20.sls` (modell: 18/19) med i18n_extra-hook;
   minioner som uppgraderar får `odoo_version`-grain 20.0 → deploy targetar dem.

## Klagomål på översättningen

Regelverk när någon påpekar "fel begrepp" eller "oöversatt":

```
1. Triage: vilken modul/utgåva/sträng? Oöversatt (tom) eller fel begrepp?
2. Sök i glossary.csv — finns termen?
   ├─ Ja, men regel saknas/täckning för liten → uppdatera rules/*.yml
   ├─ Nej → besluta term (terminologiägare) → glossary.csv + regel
   └─ Officiell ändrad till tredje variant → konflikt → beslut
   (alla fall: note med klagomålsreferens → revisionsspår)
3. ./odoosa.py build + regression (reproducera snapshot) → granska diff
4. Nästa veckosynk rullar ut automatiskt; Driftslogg loggar status
```

## Distribution

Distribution till odoo-minionerna är bakom en **explicit switch**
(`/etc/odoosa/deploy-enabled`, per minion + masterflagga) — inget distribueras
förrän flaggorna finns. Se [`docs/OPERATIONS.md`](docs/OPERATIONS.md) avsnitt 3.

**Miljöer (krav 2026-08-18):** alla odoo-minioner är klassade med
`environment`-grainet — `production` (kunder), `dev`, `test`, `infra`.
Distribution sker **endast** till `production`/`dev`/`test`; **`infra` får
aldrig översättningar** (2026-08-18: dms + pangolin reklassade till `dev` —
inga odoo-minioner i infra). Dubbelt skydd:
deploy-scriptet targetar `-C 'G@odoo:true and not G@environment:infra'` och
deploy-staten skippar själv alla som inte är `production`/`dev`/`test`.

## Säkerhet

- Inga hemligheter i detta repo. GitHub-push sker via SSH-nyckel (vertelbot),
  lagrad i Salt-pillar — aldrig i koden eller filerna här.
- Rota hemligheter som exponerats (se changelog/kommunikation).
- Salt-mastern rör aldrig GitHub; endast arbetsminionen gör det.

---

## Licens

AGPL-3 — Copyright (C) 2026 Vertel Sverige AB
