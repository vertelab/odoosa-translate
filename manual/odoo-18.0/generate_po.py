#!/usr/bin/env python3
"""Generate Swedish .po files for mail templates.

Reads the English body_html from the production DB, applies a careful
text-only translation (preserving all HTML structure and Odoo template
tags), and writes .po files to manual/odoo-18.0/.
"""

import os
import re
import sys
import subprocess
import polib


# ============================================================
# Translation dictionaries: map English text -> Swedish text
# These are applied ONLY to visible text content, never to
# HTML tags, attributes, t-* expressions, or {{ }} moustaches.
#
# IMPORTANT: Keys are matched longest-first with word boundaries.
# Do NOT add short ambiguous keys like "You" or "is" — instead
# add full phrases.
# ============================================================

# Shared phrases used across templates
COMMON = {
    # Greetings
    "Hello": "Hej",
    "Hello,": "Hej,",
    "Dear": "Bästa",
    # Thanks
    "Thank you,": "Tack,",
    "Thanks,": "Tack,",
    "Thank you for your trust!": "Tack för ditt förtroende!",
    # Contact
    "Do not hesitate to contact us if you have any questions.": "Tveka inte att kontakta oss om du har några frågor.",
    # Calendar common
    "View": "Visa",
    "(View Map)": "(Visa karta)",
    "Details of the event": "Detaljer om händelsen",
    "Location:": "Plats:",
    "When:": "När:",
    "Duration:": "Varaktighet:",
    "Attendees": "Deltagare",
    "How to Join:": "Så här ansluter du:",
    "Join with Odoo Discuss": "Anslut med Odoo Discuss",
    "Join at": "Anslut via",
    "Description of the event:": "Beskrivning av händelsen:",
    "Internal meeting for discussion for new pricing for product and services.": "Internt möte för diskussion om ny prissättning för produkter och tjänster.",
    "You": "Du",
    # Auth/portal common
    "Your Account": "Ditt konto",
    "Powered by": "Drivs av",
}

# ============================================================
# Per-template translations
# ============================================================

# --- sale / email_template_edi_sale (Send Quotation) ---
SALE_QUOTATION = dict(COMMON)
SALE_QUOTATION.update({
    "Pro forma invoice for": "Proformafaktura för",
    "with reference:": "med referens:",
    "amounting in": "med totalbelopp",
    "is available.": "är tillgänglig.",
    "is ready for review.": "är redo för granskning.",
    "Here are some additional documents that may interest you:": "Här är några ytterligare dokument som kan vara av intresse för dig:",
    "Here is an additional document that may interest you:": "Här är ett ytterligare dokument som kan vara av intresse för dig:",
    "Your": "Din",
    "quotation": "offert",
})

# --- sale / mail_template_sale_cancellation ---
SALE_CANCELLATION = dict(COMMON)
SALE_CANCELLATION.update({
    "Please be advised that your": "Vi vill informera dig om att din",
    "(with reference:": "(med referens:",
    "has been cancelled. Therefore, you should not be charged further for this order.": "har avbrutits. Du kommer därför inte att debiteras ytterligare för denna order.",
    "If any refund is necessary, this will be executed at best convenience.": "Om någon återbetalning är nödvändig kommer den att utföras snarast möjligt.",
    "quotation": "offert",
})

# --- sale / mail_template_sale_payment_executed ---
SALE_PAYMENT = dict(COMMON)
SALE_PAYMENT.update({
    "A payment with reference": "En betalning med referens",
    "amounting": "med belopp",
    "for your order": "för din order",
    "is pending.": "väntar på bekräftelse.",
    "Your order will be confirmed once the payment is confirmed.": "Din order kommer att bekräftas när betalningen har bekräftats.",
    "Once confirmed,": "När betalningen har bekräftats,",
    "will remain to be paid.": "återstår att betala.",
    "has been confirmed.": "har bekräftats.",
    "remains to be paid.": "återstår att betala.",
    "Your payment reference is": "Din betalningsreferens är",
})

# --- sale / mail_template_sale_confirmation ---
SALE_CONFIRMATION = dict(COMMON)
SALE_CONFIRMATION.update({
    "Your order": "Din order",
    "amounting in": "med totalbelopp",
    "has been confirmed.": "har bekräftats.",
    "is pending. It will be confirmed when the payment is received.": "väntar på bekräftelse. Den kommer att bekräftas när betalningen har mottagits.",
    "Your payment reference is": "Din betalningsreferens är",
    "Here are some additional documents that may interest you:": "Här är några ytterligare dokument som kan vara av intresse för dig:",
    "Here is an additional document that may interest you:": "Här är ett ytterligare dokument som kan vara av intresse för dig:",
    "Products": "Produkter",
    "Quantity": "Antal",
    "Tax Excl.": "Exkl. moms",
    "Tax Incl.": "Inkl. moms",
    "Product image": "Produktbild",
    "Subtotal:": "Delsumma:",
    "Delivery:": "Leverans:",
    "Untaxed Amount:": "Belopp exkl. moms:",
    "Taxes:": "Moms:",
    "Total:": "Totalt:",
    "Bill to:": "Faktura till:",
    "Payment Method:": "Betalningsmetod:",
    "Ship to:": "Leverera till:",
    "Shipping Method:": "Leveranssätt:",
    "(Free)": "(Gratis)",
    "Shipping Description:": "Leveransbeskrivning:",
})

# --- calendar / calendar_template_meeting_invitation ---
CAL_INVITATION = dict(COMMON)
CAL_INVITATION.update({
    "You have been invited by Customer to the": "Du har blivit inbjuden av Kunden till",
    "meeting.": "mötet.",
    "invited you for the": "har bjudit in dig till",
    "Your meeting": "Ditt möte",
    "has been booked.": "har bokats.",
    "Every 1 Weeks, for 3 events": "Varje vecka, i 3 händelser",
})

# --- calendar / calendar_template_meeting_changedate ---
CAL_CHANGEDATE = dict(COMMON)
CAL_CHANGEDATE.update({
    "The date of your appointment with": "Datumet för ditt möte med",
    "has been updated.": "har uppdaterats.",
    "Your appointment has been updated.": "Ditt möte har uppdaterats.",
    "The appointment": "Mötet",
    "is now scheduled for": "är nu schemalagt för",
    "Schedule a Demo": "Boka en demo",
    "The date of the meeting has been updated.": "Datumet för mötet har uppdaterats.",
    "The meeting": "Mötet",
    "created by": "skapat av",
    "Every 1 Weeks, for 3 events": "Varje vecka, i 3 händelser",
})

# --- calendar / calendar_template_meeting_reminder ---
CAL_REMINDER = dict(COMMON)
CAL_REMINDER.update({
    "This is a reminder for the below event:": "Detta är en påminnelse om följande händelse:",
    "Every 1 Weeks, for 3 events": "Varje vecka, i 3 händelser",
})

# --- auth_signup / mail_template_user_signup_account_created ---
AUTH_SIGNUP = dict(COMMON)
AUTH_SIGNUP.update({
    "Your account has been successfully created!": "Ditt konto har skapats!",
    "Your login is": "Din inloggning är",
    "To gain access to your account, you can use the following link:": "För att få åtkomst till ditt konto kan du använda följande länk:",
    "Go to My Account": "Gå till Mitt konto",
})

# --- portal / mail_template_data_portal_welcome ---
PORTAL_WELCOME = dict(COMMON)
PORTAL_WELCOME.update({
    "Welcome to": "Välkommen till",
    "'s Portal!": ":s portal!",
    "An account has been created for you with the following login:": "Ett konto har skapats för dig med följande inloggning:",
    "Click on the button below to pick a password and activate your account.": "Klicka på knappen nedan för att välja ett lösenord och aktivera ditt konto.",
    "Activate Account": "Aktivera konto",
    "Welcome to our company's portal.": "Välkommen till vår företagsportal.",
})


# ============================================================
# Translation engine
# ============================================================

def translate_text_node(text, trans_dict):
    """Translate a single text node.
    
    Handles multi-line text nodes that may contain several sentences
    separated by newlines and whitespace. Matches longest keys first
    and uses word boundaries for short keys.
    """
    if not text.strip():
        return text
    
    result = text
    # Sort keys by length (longest first) to avoid partial matches
    for key in sorted(trans_dict.keys(), key=len, reverse=True):
        val = trans_dict[key]
        if not key:
            continue
        # Build a regex that matches the key, allowing flexible whitespace
        # between words but not across tags (there are none in text nodes)
        escaped = re.escape(key)
        # Word boundaries for safety
        pattern = r'(?<!\w)' + escaped + r'(?!\w)'
        result = re.sub(pattern, lambda m: val, result)
    return result


def translate_html(html, trans_dict):
    """Translate visible text in HTML while preserving all structure."""
    pattern = re.compile(r'(<[^>]+>)|([^<>]+)', re.DOTALL)
    
    parts = []
    for match in pattern.finditer(html):
        if match.group(1):  # It's a tag
            parts.append(match.group(1))
        else:  # It's text
            text = match.group(2)
            parts.append(translate_text_node(text, trans_dict))
    
    return ''.join(parts)


# ============================================================
# Module → template mapping
# ============================================================

TEMPLATES = {
    "sale": {
        "sale.email_template_edi_sale": SALE_QUOTATION,
        "sale.mail_template_sale_cancellation": SALE_CANCELLATION,
        "sale.mail_template_sale_payment_executed": SALE_PAYMENT,
        "sale.mail_template_sale_confirmation": None,  # handled separately (manual)
    },
    "calendar": {
        "calendar.calendar_template_meeting_invitation": CAL_INVITATION,
        "calendar.calendar_template_meeting_changedate": CAL_CHANGEDATE,
        "calendar.calendar_template_meeting_reminder": CAL_REMINDER,
    },
    "auth_signup": {
        "auth_signup.mail_template_user_signup_account_created": AUTH_SIGNUP,
    },
    "portal": {
        "portal.mail_template_data_portal_welcome": PORTAL_WELCOME,
    },
}


def get_body_from_db(module, xmlid):
    """Get English body_html from production DB."""
    cmd = [
        "sudo", "-n", "-u", "odoo", "psql", "-d", "sfa", "-t", "-A", "-c",
        f"""
        SELECT mt.body_html->>'en_US'
        FROM mail_template mt
        JOIN ir_model_data imd ON imd.res_id = mt.id AND imd.model = 'mail.template'
        WHERE imd.module = '{module}' AND imd.name = '{xmlid}'
        """
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr}")
        return None
    return result.stdout


def main():
    outdir = '/usr/share/odoosa-translate/manual/odoo-18.0'
    os.makedirs(outdir, exist_ok=True)
    
    # Import the manual confirmation translation (full HTML)
    sys.path.insert(0, outdir)
    try:
        from sale_confirmation_sv import SALE_CONFIRMATION_SV
    except ImportError:
        SALE_CONFIRMATION_SV = None
    
    for module, entries in sorted(TEMPLATES.items()):
        po = polib.POFile()
        po.metadata = {
            'Project-Id-Version': f'odoosa-{module}-manual',
            'Language': 'sv',
            'MIME-Version': '1.0',
            'Content-Type': 'text/plain; charset=UTF-8',
        }
        
        for key, trans in sorted(entries.items()):
            xmlid = key.split('.', 1)[1]
            en_body = get_body_from_db(module, xmlid)
            if en_body is None or not en_body.strip():
                print(f"  SKIP {key}: no English body found in DB")
                continue
            
            if isinstance(trans, dict):
                # Text-dictionary translation
                sv_body = translate_html(en_body, trans)
            elif trans is None and xmlid == 'mail_template_sale_confirmation':
                # Manual full-HTML translation
                if SALE_CONFIRMATION_SV is None:
                    print(f"  SKIP {key}: manual translation not available")
                    continue
                sv_body = SALE_CONFIRMATION_SV
            else:
                continue
            
            entry = polib.POEntry(
                msgid=en_body,
                msgstr=sv_body,
                occurrences=[(f'model:mail.template,body_html:{key}', '')],
            )
            entry.comment = f'module: {module}'
            po.append(entry)
            print(f"  Added {key} ({len(en_body)} EN -> {len(sv_body)} SV)")
        
        pofile_path = os.path.join(outdir, f'{module}.po')
        po.save(pofile_path)
        print(f"Saved {pofile_path}")


if __name__ == '__main__':
    main()
