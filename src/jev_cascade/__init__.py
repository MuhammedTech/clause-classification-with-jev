"""Measures how much CUAD license-agreement text Jev can Bin before an expensive model reads it.

Vocabulary throughout this package is the one fixed in `GLOSSARY.md`. In particular a Pair whose
P(yes) is at or below the Cutoff is **Binned** (discarded), and above it is **Escalated** (sent to
the expensive model). The retired terms "kept" and "keep share" meant the opposite and are not used.
"""
