# odoosa-translate
Odoo SA Translation, Vertel Style


# Glossary:
```
glossary.csv
```

# Installation:
```
(If missing!)
sudo apt install python3-polib python3-requests

curl -s https://raw.githubusercontent.com/vertelab/odoosa-translate/master/install | bash
```

# Weblate AIP KEY:
```
https://translate.odoo.com/accounts/profile/#api

jakob@odooutv18:~$ cat ~/.bashrc
# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

export ODOO_API_KEY="ROTATED-NYCKEL-BORTTAGEN"

** key is not working! :-)
```

# Execute:
```
jakob@odooutv18:~$ odooposync
🔒 Kräver sudo...
[sudo] password for jakob: 
🔄 GitHub → Odoo sync...
✅ GitHub: 3 filer: ['account', 'crm', 'hr']

🔄 [account]
📦 GitHub: 2924 översatta fraser
✅ 2924 översättningar SKRIVNA → /usr/share/core-odoo/addons/account/i18n/sv.po

🔄 [crm]
📦 GitHub: 655 översatta fraser
✅ 655 översättningar SKRIVNA → /usr/share/core-odoo/addons/crm/i18n/sv.po

🔄 [hr]
📦 GitHub: 544 översatta fraser
✅ 544 översättningar SKRIVNA → /usr/share/core-odoo/addons/hr/i18n/sv.po

```

