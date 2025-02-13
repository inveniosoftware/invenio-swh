..
    Copyright (C) 2023-2024 CERN
    Copyright (C) 2020 Cottage Labs LLP.

    invenio-swh is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Changes
=======

Version v0.13.1 (released 2025-02-13)

- Bump invenio-rdm-records to stable release.

Version v0.13.0 (released 2024-12-27)

- Bump dependencies to support Flask v3 and SQLAlchemy v2.

Version v0.12.0 (released 2024-12-13)

- swhid: add path with root directory

Version 0.11.0 (released 2024-11-22)

- record: added record SWH systemfield

Version v0.10.3 (released 2024-11-19)

- service: refactor 'origin' calculation
    * move origin calculation to API and service
    * fix 'deposit' variable reference before assign

Version 0.10.2 (released 2024-10-18)

- tasks: remove logging for invalid records

Version 0.10.1 (released 2024-10-15)

- tasks: updated polling logic to wait on max retry

Version 0.10.0 (released 2024-07-22)

- model: added context to swhid and indices
- service: added origin information for deposits
- deposits: set status to FAILED after max poll retries
- tasks: added cleanup for deposits stuck in "waiting"

Version 0.9.0 (released 2024-04-11)

- installation: remove upper bounds from dependencies

Version 0.8.0 (released 2024-04-03)

- installation: bump invenio-rdm-records to v9

Version 0.7.0 (released 2024-03-01)

- installation: lower-pin sword2

Version 0.6.0 (released 2024-02-20)

- installation: bump invenio-rdm-records

Version 0.5.0 (released 2024-02-16)

- installation: bump invenio-rdm-records

Version 0.4.0 (released 2024-01-31)

- installation: bump dependencies

Version 0.3.0 (released 2024-01-31)

- installation: bump invenio-rdm-records

Version 0.2.2 (released 2023-12-13)

- ui: added swh external resource template.
- schema: removed open terms for software fields

Version 0.2.1 (released 2023-11-30)

- ci: update PyPI release

Version 0.2.0 (released 2023-11-30)

- Initial public release.
