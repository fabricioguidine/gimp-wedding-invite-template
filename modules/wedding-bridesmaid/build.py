"""wedding-bridesmaid — bridal-party leaflets: madrinha / padrinho / casal.

Thin wrapper over ``bridal_party_blocks.run_variants``: madrinha/padrinho use
the single-role interno center; casal uses the split center (it carries
``roles`` in content.yaml). One run emits 6 XCFs ({module}_{variant}_{side}).
Shared content (couple/date/ceremony/mission/tips) sits at the top level of
content.yaml; per-variant cover/role data live under ``variants:``.
"""

import bridal_party_blocks as bp

_VARIANT_ORDER = ('madrinha', 'padrinho', 'casal')


def run(layout, content, bg_path, output_dir, module_name):
    return bp.run_variants(layout, content, bg_path, output_dir, module_name,
                           _VARIANT_ORDER)
