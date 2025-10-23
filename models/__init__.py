"""Models package initializer.

This project historically had a single large `models.py` module alongside a
`models/` package. That causes a name collision: `import models` will load the
package, not the top-level module. Many parts of the app expect the larger
`models.py` to provide methods like `User.get_by_email`.

To remain backward-compatible, prefer the top-level `models.py` when it
exists by dynamically loading it. If it's not present, fall back to the
lightweight package-local `base` module.
"""
import importlib.util
import os
import sys
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent
# Look for a sibling top-level models.py (one directory up)
_candidate = _pkg_dir.parent / 'models.py'

if _candidate.exists():
    # Load the top-level models.py under the name 'models_main' to avoid
    # confusing the import system. Then re-export the expected symbols.
    spec = importlib.util.spec_from_file_location('models_main', str(_candidate))
    models_main = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(models_main)
    except Exception:
        # If loading the big module fails, fallback to package-local base
        models_main = None

    if models_main is not None:
        # Export common names from the large module
        for name in ('User', 'Business', 'Job', 'Service', 'Application', 'Notification', 'Review', 'Activity'):
            if hasattr(models_main, name):
                globals()[name] = getattr(models_main, name)
        # Always import Statistics from .base
        from .base import Statistics
        globals()['Statistics'] = Statistics
        __all__ = [n for n in ('User', 'Business', 'Job', 'Service', 'Application', 'Notification', 'Review', 'Activity', 'Statistics') if n in globals()]
    else:
        # Fallback to local base module
        from .base import (
            User, Business, Job, Service, Application, 
            Notification, Review, Activity, Statistics
        )
        __all__ = [
            'User', 'Business', 'Job', 'Service', 'Application',
            'Notification', 'Review', 'Activity', 'Statistics'
        ]
else:
    # No top-level models.py found; use package-local implementations
    from .base import (
        User, Business, Job, Service, Application, 
        Notification, Review, Activity, Statistics
    )
    __all__ = [
        'User', 'Business', 'Job', 'Service', 'Application',
        'Notification', 'Review', 'Activity', 'Statistics'
    ]

# Import and expose search method models
from .search_methods import JobOffer, ServiceRequest, Business as SearchBusiness
__all__.extend(['JobOffer', 'ServiceRequest'])