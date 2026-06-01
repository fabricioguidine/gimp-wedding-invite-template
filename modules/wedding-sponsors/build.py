"""wedding-sponsors — wedding-sponsor leaflets: bridesmaid / groomsman / couple.

Thin wrapper over ``trifold_blocks.run_variants``: bridesmaid/groomsman use the
single-role interno center; couple uses the split center (it carries ``roles``
in content.yaml). One run emits 6 XCFs ({module}_{variant}_{side}). Shared
content (couple/date/ceremony/mission/tips) sits at the top level of
content.yaml; per-variant cover/role data live under ``variants:``.
"""

import trifold_blocks as bp

_VARIANT_ORDER = ('bridesmaid', 'groomsman', 'couple')


def run(layout, content, bg_path, output_dir, module_name):
    return bp.run_variants(layout, content, bg_path, output_dir, module_name,
                           _VARIANT_ORDER)
