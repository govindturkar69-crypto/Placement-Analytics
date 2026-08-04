from . import auth, dashboard, students, companies, placements, analytics, predict, reports, profile

_MODULES = [auth, dashboard, students, companies, placements, analytics, predict, reports, profile]


def register_all(app):
    for module in _MODULES:
        module.register(app)
