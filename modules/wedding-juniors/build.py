"""wedding-juniors — page-boy and flower-girl leaflets (junior attendants).

Thin wrapper over ``trifold_blocks.run_variants``. Both variants are
single-role; each cover shows the child illustration via ``cover.image`` and
the invite (``mission``) is per-variant. One run emits 4 XCFs.
"""

import trifold_blocks as bp

_VARIANT_ORDER = ('pageboy', 'flowergirl')


def run(layout, content, bg_path, output_dir, module_name):
    return bp.run_variants(layout, content, bg_path, output_dir, module_name,
                           _VARIANT_ORDER)
