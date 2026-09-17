"""RetLab overlay package.

Home for cross-cutting RetLab machinery that ties the fork's features together
rather than living inside one feature. The first inhabitant is the feature
registry (``features.py``) — a single, test-backed description of every RetLab
feature that has concrete wiring (a Lua plugin and/or a ``Settings`` field).
"""
