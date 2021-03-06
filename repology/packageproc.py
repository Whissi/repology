# Copyright (C) 2016 Dmitry Marakasov <amdmi3@amdmi3.ru>
#
# This file is part of repology
#
# repology is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# repology is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with repology.  If not, see <http://www.gnu.org/licenses/>.

from functools import cmp_to_key

from repology.version import VersionCompare
from repology.package import *


def PackagesetCheckFilters(packages, *filters):
    for filt in filters:
        if not filt.Check(packages):
            return False

    return True


def FillPackagesetVersions(packages):
    versions = set()
    families = set()

    for package in packages:
        if not package.ignoreversion:
            versions.add(package.version)
        families.add(package.family)

    bestversion = None
    for version in versions:
        if bestversion is None or VersionCompare(version, bestversion) > 0:
            bestversion = version

    for package in packages:
        result = VersionCompare(package.version, bestversion) if bestversion is not None else 1
        if result > 0:
            package.versionclass = PackageVersionClass.ignored
        elif result == 0:
            # XXX: if len(families) == 1 -> PackageVersionClass.unique
            package.versionclass = PackageVersionClass.newest
        else:
            package.versionclass = PackageVersionClass.outdated


def PackagesetToSummaries(packages):
    summary = {}

    state_by_repo = {}
    families = set()

    for package in packages:
        families.add(package.family)

        if package.repo not in state_by_repo:
            state_by_repo[package.repo] = {
                'has_outdated': False,
                'bestpackage': None,
                'count': 0
            }

        if package.versionclass == PackageVersionClass.outdated:
            state_by_repo[package.repo]['has_outdated'] = True,

        if state_by_repo[package.repo]['bestpackage'] is None or VersionCompare(package.version, state_by_repo[package.repo]['bestpackage'].version) > 0:
            state_by_repo[package.repo]['bestpackage'] = package

        state_by_repo[package.repo]['count'] += 1

    for repo, state in state_by_repo.items():
        resulting_class = None

        # XXX: lonely ignored package is currently lonely; should it be ignored instead?
        if state['bestpackage'].versionclass == PackageVersionClass.outdated:
            resulting_class = RepositoryVersionClass.outdated
        elif len(families) == 1:
            resulting_class = RepositoryVersionClass.lonely
        elif state['bestpackage'].versionclass == PackageVersionClass.newest:
            if state['has_outdated']:
                resulting_class = RepositoryVersionClass.mixed
            else:
                resulting_class = RepositoryVersionClass.newest
        elif state['bestpackage'].versionclass == PackageVersionClass.ignored:
            resulting_class = RepositoryVersionClass.ignored

        summary[repo] = {
            'version': state['bestpackage'].version,
            'bestpackage': state['bestpackage'],
            'versionclass': resulting_class,
            'numpackages': state['count']
        }

    return summary


def PackagesetSortByVersions(packages):
    def packages_version_cmp_reverse(p1, p2):
        return VersionCompare(p2.version, p1.version)

    return sorted(packages, key=cmp_to_key(packages_version_cmp_reverse))


def PackagesetAggregateByVersions(packages):
    versions = []

    for package in packages:
        if versions and versions[-1]['version'] == package.version and versions[-1]['versionclass'] == package.versionclass:
            versions[-1]['packages'].append(package)
        else:
            versions.append(
                {
                    'version': package.version,
                    'versionclass': package.versionclass,
                    'packages': [package],
                }
            )

    return versions
