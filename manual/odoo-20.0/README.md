# manual/odoo-20.0 — manuella översättningar för Odoo 20.0

## Status: TOM (avsiktligt)

Katalogen finns för att rutinen letar här (`load_manual_po()` i `odoosa.py`).
Inga poster i dag — och det är rätt.

## Varför 18.0-posterna inte kopierades hit

`manual/odoo-18.0/` innehåller 5 moduler (auth_signup, calendar, portal, sale,
portal m.fl.) med `mail.template`-poster som Odoo SA lämnat tomma. Vid
porteringen 2026-11-27 kontrollerades varje msgid mot `official-now.po` för
20.0:

```
0 tomma luckor att fylla, 0 kollisioner, 18 msgid borta
```

Samtliga 18 msgid:er har **ändrats mellan utgåvorna** — `body_html`-mallarna
skrevs om (nya t-uttryck, annan HTML-struktur). En kopierad text hade pekat
på fel mall och aldrig applicerats. Att översätta de nya mallarna är eget
arbete, inte en port.

## Verkliga luckor i 20.0 (att ta senare)

SA lämnar fortfarande tomma `msgstr` — men på andra ställen än i 18.0:

| Modul | Tomma poster | Varav mail.template body_html |
|---|---|---|
| spreadsheet | 2018 | 0 |
| website | 1369 | 0 |
| web | 1062 | 0 |
| mail | 1002 | 0 |
| point_of_sale | 829 | 4 |
| hr_work_entry | 619 | 0 |

## Regeln (från manual/README.md)

En post får bara ligga här om Odoo SA lämnat den **tom** i officiell sv.po.
Har SA redan en översättning tar vi över deras text och tappar deras
framtida rättelser. Kontrollera alltid före:

```bash
python3 tools/check_manual_ports.py     # jämför 18.0-posterna mot 20.0
```
