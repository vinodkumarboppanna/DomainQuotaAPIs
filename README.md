DomainQuotaAPIs

Nova V2 APIs for Domain Quota Management

Please check the following documents to understand more about this project

Blue Print -> https://blueprints.launchpad.net/nova/+spec/domain-quota-driver-api

Wiki Page -> https://wiki.openstack.org/wiki/APIs_for_Domain_Quota_Driver

Also, add new variable under nova.quota section
keystone_auth_url=http://localhost:35357/v3/

The localhost can be changed to the IP Address of the machine hosting keystone 

Files changed are

keystoneclient/access.py

keystoneclient/base.py
keystoneclient/httpclient.py
keystoneclient/v2_0/client.py
keystoneclient/v3/client.py
keystoneclient/v3/projects.py


nova/context.py
nova/exception.py
nova/quota.py
nova/api/auth.py
nova/api/openstack/extensions.py
nova/api/openstack/wsgi.py
nova/api/openstack/compute/contrib/quotas.py
nova/db/api.py
nova/db/sqlalchemy/api.py
nova/db/sqlalchemy/models.py

Files created are
nova/api/openstack/compute/contrib/domain_quotas.py
nova/db/sqlalchemy/migrate_repo/versions/230_create_domain_quotas_tables.py

and you have to run the following command to create the tables for domain quotas
nova-manage db sync
