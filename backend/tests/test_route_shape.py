"""The route-shape ratchet: every ``wcapi/`` route is the REST channel.

Bill, 2026-09-24: REST only — ``/wcapi/<model>/`` and ``/wcapi/<model>/<id>/``, the HTTP method
naming get, save or delete; commands will be ``/wcapi/<model>/<id>/<command>/``. No app names,
no aliases. ``KNOWN_VIOLATIONS`` is the
list of routes that do not conform yet, frozen at build step 1. It may only shrink:

  * a route that is neither conforming, out of the rule, nor listed fails — no new ones;
  * a listed route that no longer exists fails — take it off the list.

When the list is empty, delete it. Plan: Allie
``readmes/assessments/2026-09-24-one-route-per-verb.md`` §7.
"""
from django.urls import get_resolver

#: No record behind them: sign-in and the API's own description.
OUT_OF_RULE = frozenset({
    'wcapi/login/',
    'wcapi/logout/',
    'wcapi/me/',
    'wcapi/token/',
    'wcapi/token_refresh/',
    'wcapi/register/',
    'wcapi/signup/',
    'wcapi/schema/',
    'wcapi/swagger/',
    'wcapi/redoc/',
})

KNOWN_VIOLATIONS = frozenset({
    'wcapi/',
    'wcapi/<drf_format_suffix:format>',
    'wcapi/<str:model_name>/<str:field>/<str:from_val>/<str:to_val>/',
    'wcapi/<str:model_name>/fields/',
    'wcapi/^invoice/(?P<pk>[^/.]+)/cash_status/$',
    'wcapi/^invoice/(?P<pk>[^/.]+)/cash_status\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^invoice/(?P<pk>[^/.]+)/populate_commission/$',
    'wcapi/^invoice/(?P<pk>[^/.]+)/populate_commission\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^order/(?P<pk>[^/.]+)/convert_to_invoice/$',
    'wcapi/^order/(?P<pk>[^/.]+)/convert_to_invoice\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^order/(?P<pk>[^/.]+)/create_purchase/$',
    'wcapi/^order/(?P<pk>[^/.]+)/create_purchase\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^order/(?P<pk>[^/.]+)/populate_commission/$',
    'wcapi/^order/(?P<pk>[^/.]+)/populate_commission\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^order/(?P<pk>[^/.]+)/reserve_inventory/$',
    'wcapi/^order/(?P<pk>[^/.]+)/reserve_inventory\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^purchase/(?P<pk>[^/.]+)/receive_goods/$',
    'wcapi/^purchase/(?P<pk>[^/.]+)/receive_goods\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^purchase/(?P<pk>[^/.]+)/totals/$',
    'wcapi/^purchase/(?P<pk>[^/.]+)/totals\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^quote/(?P<pk>[^/.]+)/convert_to_order/$',
    'wcapi/^quote/(?P<pk>[^/.]+)/convert_to_order\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/^quote/(?P<pk>[^/.]+)/populate_commission/$',
    'wcapi/^quote/(?P<pk>[^/.]+)/populate_commission\\.(?P<format>[a-z0-9]+)/?$',
    'wcapi/_<str:action>/',
    'wcapi/_bootstrap/',
    'wcapi/_burndown/<int:project_id>/',
    'wcapi/_choices/',
    'wcapi/_component_parade/',
    'wcapi/_component_parade_preview/',
    'wcapi/_dev_config/',
    'wcapi/_dev_restart/',
    'wcapi/_dev_switch/',
    'wcapi/_dev_sync/',
    'wcapi/_dev_sync_status/',
    'wcapi/_image/<str:model_name>/<str:ida>/<str:size>',
    'wcapi/_inquiry/',
    'wcapi/_inquiry/start/',
    'wcapi/_layout_parade/',
    'wcapi/_manage/',
    'wcapi/_model_detail/',
    'wcapi/_model_list/',
    'wcapi/_parade_feedback/',
    'wcapi/_parade_manifest/',
    'wcapi/_parade_preview/',
    'wcapi/_permissions/',
    'wcapi/_permissions/<str:model_name>/',
    'wcapi/_qa/<str:parent_model>/<int:parent_id>/',
    'wcapi/_qa_apply/',
    'wcapi/_qa_groups/',
    'wcapi/_refs_mismatch/',
    'wcapi/_report_fields/',
    'wcapi/_resolve_template/',
    'wcapi/_sample_data/',
    'wcapi/_save_search/',
    'wcapi/_search_presets/',
    'wcapi/_selectlists/',
    'wcapi/_setting_parade_feedback/',
    'wcapi/_setting_parade_manifest/',
    'wcapi/_setting_parade_preview/',
    'wcapi/_setting_resolve/',
    'wcapi/_settings_bootstrap/',
    'wcapi/_settings_fetch_hq/',
    'wcapi/_settings_health/',
    'wcapi/_system_info/',
    'wcapi/_template_fields/',
    'wcapi/_test_parade_feedback/',
    'wcapi/_test_parade_manifest/',
    'wcapi/_test_parade_run/',
    'wcapi/_view/',
    'wcapi/_wchq_submit/',
    'wcapi/ai/alice/ask-claude/',
    'wcapi/ai/alice/ask/',
    'wcapi/ai/ask/',
    'wcapi/ai/coaching/',
    'wcapi/ai/coaching/feedback/',
    'wcapi/ai/contact/correct/',
    'wcapi/ai/contact/detect/',
    'wcapi/ai/contact/parse-confirmed/',
    'wcapi/ai/contact/parse/',
    'wcapi/ai/contact/search/',
    'wcapi/ai/debug/',
    'wcapi/ai/device-status/',
    'wcapi/ai/diagnose/',
    'wcapi/ai/episodes/detect-patterns/',
    'wcapi/ai/episodes/feed/',
    'wcapi/ai/episodes/review/',
    'wcapi/ai/episodes/review/bulk/',
    'wcapi/ai/episodes/summary/',
    'wcapi/ai/feedback/',
    'wcapi/ai/generate/',
    'wcapi/ai/health/',
    'wcapi/ai/history/',
    'wcapi/ai/modes/',
    'wcapi/ai/note/',
    'wcapi/ai/pii/correct/',
    'wcapi/ai/pii/parse/',
    'wcapi/ai/reindex/',
    'wcapi/ai/report/',
    'wcapi/ai/review/',
    'wcapi/ai/search-feedback/',
    'wcapi/ai/support/detect-patterns/',
    'wcapi/ai/support/summary/',
    'wcapi/cash/<int:cash_id>/status/',
    'wcapi/cash/checkout-pricing/<int:invoice_id>/',
    'wcapi/cash/gateway-config/',
    'wcapi/cash/history/',
    'wcapi/docs/qa/<str:parent_model>/<int:parent_id>/',
    'wcapi/docs/qa/apply/',
    'wcapi/docs/qa/groups/',
    'wcapi/docs/stats/',
    'wcapi/document/<int:document_id>/delete/',
    'wcapi/document/<int:document_id>/download/',  # step 1 made it; owed: after_get on document
    'wcapi/get/bundle_<str:name>.json',
    'wcapi/hooks/review/',
    'wcapi/hooks/submit/',
    'wcapi/init-bundle/',
    'wcapi/instance/submit/',
    'wcapi/inventory/release/<int:invoice_id>/',
    'wcapi/inventory/reserve/',
    'wcapi/jpods/invoice/',
    'wcapi/jpods/price/',
    'wcapi/jpods/trip/',
    'wcapi/jpods/ui/contacts/',
    'wcapi/jpods/ui/identify/',
    'wcapi/jpods/ui/price/',
    'wcapi/jpods/ui/stations/',
    'wcapi/jpods/ui/travel/',
    'wcapi/order/<int:pk>/convert-to-invoice/',
    'wcapi/order/<int:pk>/convert-to-purchase/',
    'wcapi/products/bom/<int:pk>/',
    'wcapi/products/inventory/adjust-bom/',
    'wcapi/products/inventory/adjust/',
    'wcapi/products/inventory/adjustments/',
    'wcapi/products/inventory/layers/',
    'wcapi/products/items/<int:item_id>/bom/propagate-cost/',
    'wcapi/products/items/<int:item_id>/bom/where-used/',
    'wcapi/products/items/<int:item_id>/serials/',
    'wcapi/products/items/<int:item_id>/serials/receive/',
    'wcapi/products/items/<int:item_id>/serials/reference/',
    'wcapi/products/items/<int:parent_id>/bom/',
    'wcapi/products/items/<int:parent_id>/bom/consume/',
    'wcapi/products/items/<int:parent_id>/bom/expand/',
    'wcapi/products/items/<int:parent_id>/bom/recalc-cost/',
    'wcapi/products/items/inventory/',
    'wcapi/products/serials/<int:serial_id>/history/',
    'wcapi/products/serials/<int:serial_id>/issue/',
    'wcapi/products/serials/<int:serial_id>/return/',
    'wcapi/products/serials/<int:serial_id>/status/',
    'wcapi/products/serials/search/',
    'wcapi/products/serials/warranty/',
    'wcapi/purchase/<int:pk>/receive-goods/',
    'wcapi/quote/<int:pk>/convert-to-order/',
    'wcapi/register-installation/',
    'wcapi/register-installation/subscribe/',
    'wcapi/report/run/',                         # step 1 made it; owed: POST /wcapi/report/<id>/run/
    'wcapi/reports/aged_receivables/',
    'wcapi/reports/gl-export/',
    'wcapi/reports/statement/<int:customer_id>/',
    'wcapi/statements/export/',
    'wcapi/statements/files/',
    'wcapi/statements/harvest/',
    'wcapi/statements/lines/',
    'wcapi/statements/promote/',
    'wcapi/statements/save/',
    'wcapi/sync/bundle/<str:bundle_uuid>/approve/',
    'wcapi/sync/bundle/<str:bundle_uuid>/status/',
    'wcapi/sync/bundle/callback/',
    'wcapi/sync/connections/',
    'wcapi/sync/connections/<int:pk>/',
    'wcapi/sync/connections/search/',
    'wcapi/sync/form-library/',
    'wcapi/sync/form-library/checkout/',
    'wcapi/sync/form-library/restore/',
    'wcapi/sync/form-library/submit/',
    'wcapi/sync/po-status/<int:pk>/<str:bundle_uuid>/',
    'wcapi/sync/po-to-so/<int:pk>/',
    'wcapi/sync/receive/',
    'wcapi/transfers/bulk/orders-to-invoices/',
    'wcapi/transfers/bulk/quotes-to-orders/',
    'wcapi/transfers/execute/',
    'wcapi/transfers/validate/',
    'wcapi/upload/',
    'wcapi/webserving/heartbeat/',
    'wcapi/webserving/register/',
    'wcapi/webserving/search/',
    'wcapi/webserving/stats/',
})


def _wcapi_routes():
    found = set()

    def walk(patterns, prefix=''):
        for p in patterns:
            if hasattr(p, 'url_patterns'):
                walk(p.url_patterns, prefix + str(p.pattern))
            else:
                found.add(prefix + str(p.pattern))

    walk(get_resolver().url_patterns)
    return {r for r in found if r.startswith('wcapi')}


#: The REST channel's own two routes (views/channel_view.py).
CHANNEL_ROUTES = frozenset({'wcapi/<str:model_name>/', 'wcapi/<str:model_name>/<int:record_id>/',
                            'wcapi/<str:model_name>/<int:record_id>/<str:command>/',
                            'wcapi/<str:model_name>/_receive/<str:provider>/'})


def _conforms(route):
    return route in CHANNEL_ROUTES


def test_no_new_route_breaks_the_shape():
    new = sorted(r for r in _wcapi_routes()
                 if not _conforms(r) and r not in OUT_OF_RULE and r not in KNOWN_VIOLATIONS)
    assert not new, ('Routes are the REST channel — /wcapi/<model>/[<id>/] — not their own '
                     'shape:\n' + '\n'.join(new))


def test_an_excluded_route_is_not_also_a_violation():
    """A route is out of the rule or not yet in it — never both, or the list cannot shrink."""
    assert not (OUT_OF_RULE & KNOWN_VIOLATIONS)


def test_the_known_violations_list_only_shrinks():
    gone = sorted(KNOWN_VIOLATIONS - _wcapi_routes())
    assert not gone, 'Fixed or removed — take these off KNOWN_VIOLATIONS:\n' + '\n'.join(gone)


def test_the_channel_routes_exist_and_come_last():
    """Last, so a named route is never shadowed by a model called the same thing."""
    from webclerk3_api.urls import urlpatterns
    patterns = [str(p.pattern) for p in urlpatterns]
    assert CHANNEL_ROUTES <= set(patterns)
    last_wcapi = [p for p in patterns if p.startswith('wcapi')][-len(CHANNEL_ROUTES):]
    assert set(last_wcapi) == CHANNEL_ROUTES
