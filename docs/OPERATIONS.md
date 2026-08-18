# odoosa-translate — Operations & Drift

> Kontinuerlig, multi-utgåva svensk översättning av Odoo-kärnan, baserad på
> Odoo SAs officiella översättningar + vår terminologi (`glossary.csv` + `rules/`).
> Överlagringar levereras via Odoos native **`i18n_extra`**-mekanism.

---

## 1. Översikt

```
                    ┌─────────────────────────────┐
                    │   ARBETSMINION "odoosa"     │  ← enda maskinen som arbetar med GitHub
                    └──────────────┬──────────────┘
                                   │  cron måndag 05:30
                                   ▼
                       odoosa.py run --versions 18.0,19.0
                       (fetch → apply → merge → build)
                                   │
        ┌──────────────────────────┼────────────────────────────┐
        ▼                          ▼                            ▼
 github.com/                SALT-MASTERN                   ledningssystem.vertel.se
 vertelab/odoosa-translate  (tar emot via cp.push)         /saltstack/log (Driftslogg)
 (publik: artefakter,       /srv/salt/odoosa-translate/    {source: odoosa}
  regler, ordlista)         build/odoo-<ver>/i18n_extra/<modul>/i18n_extra/sv.po
                                   │
                                   ▼
                         ~70 ODOO-MINIONER (18.0/19.0)
                         /usr/lib/python3/dist-packages/odoo/addons/<m>/i18n_extra/sv.po
                         + hooks i odoo/18.sls, odoo/19.sls, odoo/update.sls
```

**Principer**
- Arbetsminionen är **enda** maskinen som arbetar med GitHub (push + repo-underhåll).
- Salt-mastern rör **aldrig** GitHub — den tar emot byggartefakter via `cp.push`.
- Officiella `i18n/sv.po` rörs **aldrig**; vi äger bara avvikelser i `i18n_extra`.
- Utländska `l10n_*`-moduler översätts **aldrig** (endast `l10n_se` är relevant).

---

## 2. Snabbkommandon

### 2.1 Veckosynk & pipeline (körs på arbetsminionen)

```bash
# Hela pipelinen (fetch → apply → merge → build)
sudo salt odoosa-translate cmd.run 'cd /srv/odoosa-translate && ./odoosa.py run --versions 18.0,19.0'

# Enskilda steg
sudo salt odoosa-translate cmd.run 'cd /srv/odoosa-translate && ./odoosa.py fetch  --versions 18.0'
sudo salt odoosa-translate cmd.run 'cd /srv/odoosa-translate && ./odoosa.py apply  --versions 18.0'
sudo salt odoosa-translate cmd.run 'cd /srv/odoosa-translate && ./odoosa.py build  --versions 18.0'

# Regression mot gamla snapshots (hur nära 100 % är reglerna?)
sudo salt odoosa-translate cmd.run 'cd /srv/odoosa-translate && ./odoosa.py regression --versions 18.0'

# Ny-utgåva-procedur: verifiera i18n_extra-stöd i utgåvan
sudo salt odoosa-translate cmd.run 'cd /srv/odoosa-translate && ./odoosa.py check-edition 20.0'
```

### 2.2 Publicera till GitHub (arbetsminionen)

```bash
# Commit + push av artefakter, regler, ordlista, rapporter
sudo salt odoosa-translate cmd.run 'cd /srv/odoosa-translate && ./odoosa.py publish'

# Säker test: committar lokalt men pushar inte
sudo salt odoosa-translate cmd.run 'cd /srv/odoosa-translate && ./odoosa.py publish --dry-run'
```

### 2.3 Status & kontroll (säkert — applicerar inget)

```bash
# Ping
sudo salt odoosa-translate test.ping

# Pillar (arbetsminionen ska ha odoosa-pillar med publish_url/token/ssh-key)
sudo salt-run pillar.show_pillar odoosa-translate | grep -A5 'odoosa:'

# RENDERA deploy-staten på en odoo-minion — visar vilken gate som gäller (applicerar INGET)
sudo salt <minion> state.show_sls odoosa.deploy

# Veckorapporten
sudo salt odoosa-translate cmd.run 'cat /srv/odoosa-translate/reports/odoosa-18.0-report.md'

# Loggar
sudo salt odoosa-translate cmd.run 'tail -30 /var/log/odoosa/pipeline.log'
```

---

## 3. Distribution — aktivering (explicit switch)

Distribution sker **inte** automatiskt. Den är bakom en flagg-fil på varje
odoo-minion + en masterflagga. Aktivera först när allt är kontrollerat:

```bash
# 1. Masterflagga (global switch)
sudo salt SaltStack state.apply odoosa.enable

# 2. Veckocron på mastern (måndag 06:00 — packar upp + distribuerar)
sudo salt SaltStack state.apply odoosa.deploy_cron

# 3. Minionflaggor (tillåter distribution på production/dev/test-minioner)
sudo salt -C 'G@odoo:true and not G@environment:infra' state.apply odoosa.enable
```

Efter aktivering:
- **Veckocron** (måndag 06:00) distribuerar nya översättningar automatiskt.
- **Varannan-vecka-uppdateringen** (`odoo.update`, 7:e/21:e) tar med
  översättningarna efter varje nightly-install (paketet torkar paketkatalogen).

### Deaktivera

```bash
sudo salt -C 'G@odoo:true and not G@environment:infra' cmd.run 'rm -f /etc/odoosa/deploy-enabled'
sudo salt SaltStack cmd.run 'rm -f /etc/odoosa/deploy-enabled'
```

### Manuell distribution nu

```bash
# Skicka bygget från arbetsminionen → mastern
sudo salt odoosa-translate cmd.run '/usr/local/bin/odoosa-sync-master.sh'

# Packa upp + distribuera (kräver masterflagga + minionflaggor)
sudo salt SaltStack cmd.run '/usr/local/bin/odoosa-deploy.sh'

# Eller direkt deploy (kräver minionflaggor; infra exkluderas)
sudo salt -C 'G@odoo:true and not G@environment:infra' state.apply odoosa.deploy
```

---

## 4. Gates — fem lager

| # | Gate | Kontroll | Utan → |
|---|------|----------|--------|
| 1 | `odoo_version`-grain | minionen är odoo-server | "inte odoo-server" — no-op |
| 2 | `environment`-grain | endast `production` (kunder), `dev`, `test` | **ALDRIG `infra`** — no-op med notis |
| 3 | `/etc/odoosa/deploy-enabled` | per minion (`odoosa.enable`) | no-op med notis |
| 4 | Byggartefakter i filroten | `salt://odoosa-translate/build/odoo-<ver>/i18n_extra` | no-op med notis |
| 5 | SA-ONLY | i18n_extra innehåller bara odoo/odoo-moduler (i18n_extra ⊆ officiella `i18n/`-spegel) | deploy vägras HÅRT |

**Miljöer (krav 2026-08-18):** alla odoo-minioner är klassade med
`environment`-grainet: `production` (kunder), `dev`, `test`, `infra`.
Distribution sker **endast** till `production`/`dev`/`test`; **`infra`
(dms, pangolin.vertel.se m.fl.) får aldrig översättningar**. Dubbelt skydd:
`odoosa-deploy.sh` targetar `-C 'G@odoo:true and not G@environment:infra'` och
`odoosa.deploy`/`odoo/19.sls` skippar själva om `environment` inte är
`production`/`dev`/`test` (eller saknas).

`file.recurse` skriver endast hash-ändrade filer → idempotent, ingen onödig I/O.

---

## 5. Regler & terminologi

| Fil | Roll |
|-----|------|
| `glossary.csv` | Version-agnostisk termbas (`source,target`) — källa för begrepp |
| `rules/core.yml` | Delad regelkärna (`versions: [18, 19]`, `modules: "*"` eller lista) |
| `rules/odoo-<edition>.yml` | Versionsspecifikt (samma `id` överridar kärnan) |

**Semantik**
- Regler appliceras på **msgstr** (aldrig msgid), **längsta match först**.
- `only_if_msgid` = regex som måste matcha msgid (t.ex. Företag→Bolag bara när
  msgid innehåller `Company`/`Companies` — inte `Corporate`/`Business`).
- Lägga till/ändra term: sök i `glossary.csv` → uppdatera YAML (med `note`
  = klagomålsreferens) → `odoosa.py build` + regression → nästa veckosynk rullar ut.

---

## 6. Trevägs-merge — användarfallen

| Användarfall | Förra officiella | Nu officiella | Vår vilja | Beslut |
|---|---|---|---|---|
| Översatt, fel begrepp | Bokföringspost | Bokföringspost | Verifikat | **Override** → i18n_extra |
| Konvergerat 🎉 | Bokföringspost | Verifikat | Verifikat | Släpp vår post |
| Konflikt ⚠️ | Bokföringspost | Bokföringspost (rad) | Verifikat | Behåll vår + flagga |
| Oöversatt, vi har term | (tom) | (tom) | Verifikat | Fyll via ordlista/regel |
| Oöversatt, ingen term | (tom) | (tom) | (—) | Lämna + flagga manuell |
| Ny från Odoo, redan rätt | — | Verifikat | — | Ingen åtgärd |
| Ny från Odoo, fel begrepp | — | Bokföringspost | Verifikat | Korrigera via regel |
| Borttagen i Odoo | Bokföringspost | — | Verifikat | Städa bort vår post |

---

## 7. Felsökning

| Symtom | Åtgärd |
|--------|--------|
| `Permission denied (publickey)` vid push | `.pub`-filen stale? → `ssh-keygen -y -f /root/.ssh/odoosa_translate > /root/.ssh/odoosa_translate.pub`. Nyckeln (vertelbot) registrerad på GitHub? |
| `cp.push` misslyckas | `file_recv: True` i `/etc/salt/master.d/odoosa.conf` — filnamnet MÅSTE vara `*.conf` (`master.d/master` läses inte!) |
| `odoosa.deploy` visar notis | Identifiera vilken gate som gäller (grain / flagga / artefakter) |
| Artefakter saknas på mastern | Kör `odoosa-sync-master.sh` på arbetsminionen; kolla `/var/cache/salt/master/minions/odoosa-translate/files/tmp/odoosa-build.tgz` |
| Rapport uteblir i Driftslogg | `tail /var/log/odoosa/publish.log`; token i `/etc/odoosa/publish.conf` (delad med `/saltstack/alert`) |
| State-renderfel | `salt <minion> state.show_sls odoosa` och läs Salt-felet (t.ex. indrag i `pillar/top.sls` = nyckel 14, lista 16) |

---

## 8. Veckocykeln (referens)

| När | Vem | Vad |
|-----|-----|-----|
| Söndag | Weblate → Odoo SA | Nya översättningar i officiella filer |
| Måndag 05:30 | Arbetsminion | `run` → `publish` (GitHub) → `sync-master` (cp.push) → Driftslogg |
| Måndag 06:00 | Salt-mastern | (om aktiverat) packa upp + `salt -G 'odoo:true' state.apply odoosa.deploy` |
| 7:e/21:e 02:30 | Odoo-minioner | `odoo.update` (nightly) + i18n_extra-hook (efter install) |

---

## 9. Kända lärdomar

- `salt['file.file_exists']` i Jinja renderas mot **minionen**, inte mastern.
- `git.latest` är fel verktyg för en arbetsrepo (vill återställa till origin) — använd idempotent clone-if-missing.
- Privata nycklar lagras i pillar (`odoosa:github_ssh_key`) och levereras endast till arbetsminionen.
- Se även skill: `odoo-translation` (terminologi & i18n_extra-mekanismen) och `odoosa-translate` (drift).
- **`build_i18n_extra` måste ALLTID sätta `module: <modul>`-kommentar** (regex+prepend, INTE bara tom-fallback) — Odoo 18:s TranslationFileReader (translate.py:831) kraschar med `AttributeError` på poster utan `module[s]: (\w+)`-kommentar (driftlärdom 2026-08-14 + 2026-08-17).
- **VALIDATE-gate**: `odoosa.py build` avslutar med `validate_i18n_extra()` som skannar alla i18n_extra-poster och RAISAR (→ kedjan bryts → ingen publish/deploy) om någon post saknar module:-kommentar.
- **Publish gör `git pull --rebase origin main` före push** — annars `rejected HEAD -> main (fetch first)` (hände 2026-08-17 05:30) → cronkedjan `&&` bryts tyst → sync-master körs inte → masterns deploy använder en GAMMAL tgz.
- **Masterns odoosa-deploy.sh avbryter om tgz är äldre än 48h** — en misslyckad veckosynk får aldrig distribuera föråldrade artefakter.
- **Kodändringar i odoosa.py MÅSTE publiceras till GitHub** (arbetsminionen klonar därifrån; en fix bara i /srv/salt-repot räcker inte — se 2026-08-17).
