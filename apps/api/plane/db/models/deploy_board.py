# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Published boards were removed. Historical migrations (0041, 0067) still import these helpers
# as field defaults, so they must stay importable.

# Python imports
from uuid import uuid4


def get_anchor():
    return uuid4().hex
