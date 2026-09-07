#!/usr/bin/env python3
"""Swedish translation for sale.mail_template_sale_confirmation (the big one)."""

SALE_CONFIRMATION_SV = """<div style="margin: 0px; padding: 0px;">
    <p style="margin: 0px; padding: 0px; font-size: 12px;">
        Hej,
        <br/><br/>
        <t t-set="tx_sudo" t-value="object.get_portal_last_transaction()"/>
        Din order <span style="font-weight:bold;" t-out="object.name or ''">S00049</span> med totalbelopp <span style="font-weight:bold;" t-out="format_amount(object.amount_total, object.currency_id) or ''">$ 10.00</span>
        <t t-if="object.state == 'sale' or (tx_sudo and tx_sudo.state in ('done', 'authorized'))">
            har bekräftats.<br/>
            Tack för ditt förtroende!
        </t>
        <t t-elif="tx_sudo and tx_sudo.state == 'pending'">
            väntar på bekräftelse. Den kommer att bekräftas när betalningen har mottagits.
            <t t-if="object.reference">
                Din betalningsreferens är <span style="font-weight:bold;" t-out="object.reference or ''"/>.
            </t>
        </t>
        <br/>
        <t t-set="documents" t-value="object._get_product_documents()"/>
        <t t-if="documents">
            <br/> 
            <t t-if="len(documents)&gt;1">
                Här är några ytterligare dokument som kan vara av intresse för dig:
            </t>
            <t t-else="">
                Här är ett ytterligare dokument som kan vara av intresse för dig:
            </t>
            <ul style="margin-bottom: 0;">
                <t t-foreach="documents" t-as="document">
                    <li style="font-size: 13px;">
                        <a t-out="document.ir_attachment_id.name" t-att-href="object.get_portal_url('/document/' + str(document.id))" t-att-target="target"/>
                    </li>
                </t>
            </ul>
        </t>
        <br/>
        Tveka inte att kontakta oss om du har några frågor.
        <t t-if="not is_html_empty(object.user_id.signature)" data-o-mail-quote-container="1">
            <br/><br/>
            <t t-out="object.user_id.signature or ''" data-o-mail-quote="1">--<br data-o-mail-quote="1"/>Mitchell Admin</t>
        </t>
        <br/><br/>
    </p>
<t t-if="hasattr(object, 'website_id') and object.website_id">
    <div style="margin: 0px; padding: 0px;">
        <table width="100%" style="color: #454748; font-size: 12px; border-collapse: collapse; white-space: nowrap;">
            <tr style="border-bottom: 2px solid #dee2e6;">
                <td style="width: 150px;"><span style="font-weight:bold;">Produkter</span></td>
                <td/>
                <td width="15%" align="center"><span style="font-weight:bold;">Antal</span></td>
                <td width="20%" align="right">
                    <span style="font-weight:bold;">
                        <t t-if="object.website_id.show_line_subtotals_tax_selection == 'tax_excluded'">
                            Exkl. moms
                        </t>
                        <t t-else="">
                            Inkl. moms
                        </t>
                    </span>
                </td>
            </tr>
        </table>
        <t t-set="current_subtotal" t-value="0"/>
        <t t-foreach="object.order_line" t-as="line">
            <t t-set="line_subtotal" t-value="                     line.price_subtotal                     if object.website_id.show_line_subtotals_tax_selection == 'tax_excluded'                     else line.price_total                 "/>
            <t t-set="current_subtotal" t-value="current_subtotal + line_subtotal"/>
            <t t-if="(not hasattr(line, 'is_delivery') or not line.is_delivery) and (                     line.display_type in ['line_section', 'line_note']                     or line.product_type == 'combo'                 )">
                <table width="100%" style="color: #454748; font-size: 12px; border-collapse: collapse;">
                    <t t-set="loop_cycle_number" t-value="loop_cycle_number or 0"/>
                    <tr t-att-style="'background-color: #f2f2f2' if loop_cycle_number % 2 == 0 else 'background-color: #ffffff'">
                        <t t-set="loop_cycle_number" t-value="loop_cycle_number + 1"/>
                        <td colspan="4">
                            <t t-if="line.display_type == 'line_section' or line.product_type == 'combo'">
                                <span style="font-weight:bold;" t-out="line.name or ''">Taking care of Trees Course</span>
                                <t t-set="current_section" t-value="line"/>
                                <t t-set="current_subtotal" t-value="0"/>
                            </t>
                            <t t-elif="line.display_type == 'line_note'">
                                <i t-out="line.name or ''">Taking care of Trees Course</i>
                            </t>
                        </td>
                    </tr>
                </table>
            </t>
            <t t-elif="(not hasattr(line, 'is_delivery') or not line.is_delivery)">
                <table width="100%" style="color: #454748; font-size: 12px; border-collapse: collapse;">
                    <t t-set="loop_cycle_number" t-value="loop_cycle_number or 0"/>
                    <tr t-att-style="'background-color: #f2f2f2' if loop_cycle_number % 2 == 0 else 'background-color: #ffffff'">
                        <t t-set="loop_cycle_number" t-value="loop_cycle_number + 1"/>
                        <td style="width: 150px;">
                            <img t-attf-src="/web/image/product.product/{{ line.product_id.id }}/image_128" style="width: 64px; height: 64px; object-fit: contain;" alt="Produktbild"/>
                        </td>
                        <td align="left" t-out="line.product_id.name or ''">	Taking care of Trees Course</td>
                        <td width="15%" align="center" t-out="line.product_uom_qty or ''">1</td>
                        <td width="20%" align="right"><span style="font-weight:bold; white-space: nowrap;">
                        <t t-if="object.website_id.show_line_subtotals_tax_selection == 'tax_excluded'">
                            <t t-out="format_amount(line.price_reduce_taxexcl, object.currency_id) or ''">$ 10.00</t>
                        </t>
                        <t t-else="">
                            <t t-out="format_amount(line.price_reduce_taxinc, object.currency_id) or ''">$ 10.00</t>
                        </t>
                        </span></td>
                    </tr>
                </table>
            </t>
            <t t-if="current_section and (                     line_last                     or object.order_line[line_index+1].display_type == 'line_section'                     or object.order_line[line_index+1].product_type == 'combo'                     or (                         line.combo_item_id                         and not object.order_line[line_index+1].combo_item_id                     )                 ) and not line.is_downpayment">
                <t t-set="current_section" t-value="None"/>
                <table width="100%" style="color: #454748; font-size: 12px; border-collapse: collapse;">
                    <t t-set="loop_cycle_number" t-value="loop_cycle_number or 0"/>
                    <tr t-att-style="'background-color: #f2f2f2' if loop_cycle_number % 2 == 0 else 'background-color: #ffffff'">
                        <t t-set="loop_cycle_number" t-value="loop_cycle_number + 1"/>
                        <td style="width: 100%" align="right">
                            <span style="font-weight: bold;">Delsumma:</span>
                            <span t-out="format_amount(current_subtotal, object.currency_id) or ''">$ 10.00</span>
                        </td>
                    </tr>
                </table>
            </t>
        </t>
    </div>
    <div style="margin: 0px; padding: 0px;" t-if="hasattr(object, 'carrier_id') and object.carrier_id">
        <table width="100%" style="color: #454748; font-size: 12px; border-spacing: 0px 4px; white-space: nowrap;" align="right">
            <tr>
                <td style="width: 60%"/>
                <td style="width: 30%; border-top: 1px solid #dee2e6;" align="right"><span style="font-weight:bold;">Leverans:</span></td>
                <td style="width: 10%; border-top: 1px solid #dee2e6;" align="right" t-out="format_amount(object.amount_delivery, object.currency_id) or ''">$ 0.00</td>
            </tr>
            <tr>
                <td style="width: 60%"/>
                <td style="width: 30%;" align="right"><span style="font-weight:bold;">Belopp exkl. moms:</span></td>
                <td style="width: 10%;" align="right" t-out="format_amount(object.amount_untaxed, object.currency_id) or ''">$ 10.00</td>
            </tr>
        </table>
    </div>
    <div style="margin: 0px; padding: 0px;" t-else="">
        <table width="100%" style="color: #454748; font-size: 12px; border-spacing: 0px 4px; white-space: nowrap;" align="right">
            <tr>
                <td style="width: 60%"/>
                <td style="width: 30%; border-top: 1px solid #dee2e6;" align="right"><span style="font-weight:bold;">Belopp exkl. moms:</span></td>
                <td style="width: 10%; border-top: 1px solid #dee2e6;" align="right" t-out="format_amount(object.amount_untaxed, object.currency_id) or ''">$ 10.00</td>
            </tr>
        </table>
    </div>
    <div style="margin: 0px; padding: 0px;">
        <table width="100%" style="color: #454748; font-size: 12px; border-spacing: 0px 4px; white-space: nowrap;" align="right">
            <tr>
                <td style="width: 60%"/>
                <td style="width: 30%;" align="right"><span style="font-weight:bold;">Moms:</span></td>
                <td style="width: 10%;" align="right" t-out="format_amount(object.amount_tax, object.currency_id) or ''">$ 0.00</td>
            </tr>
            <tr>
                <td style="width: 60%"/>
                <td style="width: 30%; border-top: 1px solid #dee2e6;" align="right"><span style="font-weight:bold;">Totalt:</span></td>
                <td style="width: 10%; border-top: 1px solid #dee2e6;" align="right" t-out="format_amount(object.amount_total, object.currency_id) or ''">$ 10.00</td>
            </tr>
        </table>
    </div>
    <div t-if="object.partner_invoice_id" style="margin: 0px; padding: 0px;">
        <table width="100%" style="color: #454748; font-size: 12px;">
            <tr>
                <td style="padding-top: 10px;">
                    <span style="font-weight:bold;">Faktura till:</span>
                    <t t-out="object.partner_invoice_id.street or ''">1201 S Figueroa St</t>
                    <t t-out="object.partner_invoice_id.city or ''">Los Angeles</t>
                    <t t-out="object.partner_invoice_id.state_id.name or ''">California</t>
                    <t t-out="object.partner_invoice_id.zip or ''">90015</t>
                    <t t-out="object.partner_invoice_id.country_id.name or ''">United States</t>
                </td>
            </tr>
            <tr>
                <td>
                    <span style="font-weight:bold;">Betalningsmetod:</span>
                    <t t-if="tx_sudo.token_id">
                        <t t-out="tx_sudo.token_id.display_name or ''"/>
                    </t>
                    <t t-else="">
                        <t t-out="tx_sudo.provider_id.sudo().name or ''"/>
                    </t>
                    (<t t-out="format_amount(tx_sudo.amount, object.currency_id) or ''">$ 10.00</t>)
                </td>
            </tr>
        </table>
    </div>
    <div t-if="object.partner_shipping_id and not object.only_services" style="margin: 0px; padding: 0px;">
        <table width="100%" style="color: #454748; font-size: 12px;">
            <tr>
                <td>
                    <br/>
                    <span style="font-weight:bold;">Leverera till:</span>
                    <t t-out="object.partner_shipping_id.street or ''">1201 S Figueroa St</t>
                    <t t-out="object.partner_shipping_id.city or ''">Los Angeles</t>
                    <t t-out="object.partner_shipping_id.state_id.name or ''">California</t>
                    <t t-out="object.partner_shipping_id.zip or ''">90015</t>
                    <t t-out="object.partner_shipping_id.country_id.name or ''">United States</t>
                </td>
            </tr>
        </table>
        <table t-if="hasattr(object, 'carrier_id') and object.carrier_id" width="100%" style="color: #454748; font-size: 12px;">
            <tr>
                <td>
                    <span style="font-weight:bold;">Leveranssätt:</span>
                    <t t-out="object.carrier_id.name or ''"/>
                    <t t-if="object.amount_delivery == 0.0">
                        (Gratis)
                    </t>
                    <t t-else="">
                        (<t t-out="format_amount(object.amount_delivery, object.currency_id) or ''">$ 10.00</t>)
                    </t>
                </td>
            </tr>
            <tr t-if="object.carrier_id.carrier_description">
                <td>
                    <strong>Leveransbeskrivning:</strong>
                    <t t-out="object.carrier_id.carrier_description"/>
                </td>
            </tr>
        </table>
    </div>
</t>
</div>"""
