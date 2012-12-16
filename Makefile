# This file is part of lisogo
#
# :copyright: © Martin Richard - martiusweb.net
# :license: Released under GNU/GPLv2 license

BOOTSTRAP_DIR = vendor/bootstrap

LISOGO_LESS = frontend/less/lisogo.less
FRONTEND_STATIC_DIR = frontend/less/lisogo.less

STATIC_DIR = lisogo/static
LISOGO_CSS = lisogo.css

stylesheet: bootstrap
	recess --compile ${LISOGO_LESS} > ${STATIC_DIR}/${LISOGO_CSS}
	cp -r ${BOOTSTRAP_DIR}/img ${STATIC_DIR}
	mkdir -p ${STATIC_DIR}/js/vendor/bootstrap
	cp -r ${BOOTSTRAP_DIR}/js ${STATIC_DIR}/js/vendor/bootstrap

bootstrap:
	cd ${BOOTSTRAP_DIR}/ && make
