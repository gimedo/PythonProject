class DevelopmentConfig():
    DEBUG = True
    MYSQL_HOST ='192.168.50.8'
    MYSQL_USER ='sistemas'
    MYSQL_PASSWORD ='CH4W4RM43000%%'
    MYSQL_DB = 'xtest'

        # Configuración PostgreSQL
    POSTGRESQL_HOST = '192.168.60.60'
    POSTGRESQL_PORT = 5432
    POSTGRESQL_USER = 'sistemas'
    POSTGRESQL_PASSWORD = 'Raizen3000'
    POSTGRESQL_DB = 'api_ventas'


config={
    'development': DevelopmentConfig

}