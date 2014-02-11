# Copyright 2013 NEC Corporation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from migrate.changeset import UniqueConstraint
from migrate import ForeignKeyConstraint
from sqlalchemy import Column, DateTime, Index
from sqlalchemy import MetaData, Integer, String, Table

from nova.db.sqlalchemy import utils
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def upgrade(migrate_engine):
    meta = MetaData(bind=migrate_engine)

    domain_quota = Table('domain_quotas', meta,
            Column('id', Integer, primary_key=True, nullable=False),
            Column('created_at', DateTime),
            Column('updated_at', DateTime),
            Column('deleted_at', DateTime),
            Column('deleted', Integer),
            Column('domain_id', String(255)),
            Column('resource', String(255), nullable=False),
            Column('hard_limit', Integer()),
            mysql_engine='InnoDB',
            mysql_charset='utf8')

    domain_quota_usage = Table('domain_quota_usages', meta,
            Column('id', Integer, primary_key=True, nullable=False),
            Column('created_at', DateTime),
            Column('updated_at', DateTime),
            Column('deleted_at', DateTime),
            Column('deleted', Integer),
            Column('domain_id', String(255)),
            Column('resource', String(255), nullable=False),
            Column('in_use', Integer, nullable=False),
            Column('reserved', Integer, nullable=False),
            Column('until_refresh', Integer),
            mysql_engine='InnoDB',
            mysql_charset='utf8')

    domain_reservation = Table('domain_reservations', meta,
        Column('id', Integer, primary_key=True, nullable=False),
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Integer),
        Column('uuid', String(length=36), nullable=False),
        Column('domain_id', String(255)),
        Column('usage_id', Integer, nullable=False),
        Column('resource', String(length=255)),
        Column('delta', Integer, nullable=False),
        Column('expire', DateTime),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    tables = [domain_quota, domain_quota_usage, domain_reservation]

    for table in tables:
        try:
            table.create()
            utils.create_shadow_table(migrate_engine, table=table)
        except Exception:
            LOG.info(repr(table))
            LOG.exception(_('Exception while creating table.'))
            raise

    indexes = [
               Index('domain_quotas_domain_id_deleted_idx',
                     'domain_id', 'deleted'),

               #DomainQuotaUsages
               Index('ix_domain_quota_usages_domain_id', 'domain_id'),

               #DomainReservation
               Index('ix_domain_reservations_id', 'domain_id'),
               Index('domain_reservations_uuid_idx', 'uuid'),
               ]

    # Common indexes
    # for index in indexes:
    #    print "<<<<<<<<<<<<<<<INDEXES>>>>>>>>>>>>>>>>>>>"
    #    print index
    #    index.create(migrate_engine)

    fkeys = [
             [[domain_reservation.c.usage_id],
                  [domain_quota_usage.c.id],
                  'domain_reservations_ibfk_1']
             ]

    for fkey_pair in fkeys:
        if migrate_engine.name == 'mysql':
            # For MySQL we name our fkeys explicitly so they match Folsom
            fkey = ForeignKeyConstraint(columns=fkey_pair[0],
                                   refcolumns=fkey_pair[1],
                                   name=fkey_pair[2])
            fkey.create()
        elif migrate_engine.name == 'postgresql':
            # PostgreSQL names things like it wants (correct and compatible!)
            fkey = ForeignKeyConstraint(columns=fkey_pair[0],
                                   refcolumns=fkey_pair[1])
            fkey.create()

    uniq_name = "uniq_domain_quotas0domain_id0resource0deleted"
    uc_domain_quota = UniqueConstraint("domain_id", "resource", "deleted",
                                       table=domain_quota, name=uniq_name)
    uc_domain_quota.create()


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    domain_quota = Table('domain_quotas', meta, autoload=True)
    domain_quota_usage = Table('domain_quota_usages', meta, autoload=True)
    domain_reservation = Table('domain_reservations', meta, autoload=True)
    shadow_domain_quota = Table('shadow_domain_quotas', meta, autoload=True)
    shadow_domain_quota_usage = Table('shadow_domain_quota_usages',
                                      meta, autoload=True)
    shadow_domain_reservation = Table('shadow_domain_reservations',
                                      meta, autoload=True)

    domain_table = [domain_quota, domain_quota_usage,
                    domain_reservation,
                    shadow_domain_quota, shadow_domain_quota_usage,
                    shadow_domain_reservation]
    for table in domain_table:
        try:
            table.drop()
        except Exception:
            LOG.error(_("Domain table not dropped"))
            raise
