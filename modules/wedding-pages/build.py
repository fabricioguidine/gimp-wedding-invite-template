"""wedding-pages — manuais do Pajem e da Daminha (variantes infantis).

Thin wrapper over ``bridal_party_blocks.run_variants``. Both variants are
single-role; each cover shows the child illustration via ``cover.image`` and
the convite (``mission``) is per-variant. One run emits 4 XCFs.
"""

import bridal_party_blocks as bp

_VARIANT_ORDER = ('pajem', 'daminha')


def run(layout, content, bg_path, output_dir, module_name):
    return bp.run_variants(layout, content, bg_path, output_dir, module_name,
                           _VARIANT_ORDER)
