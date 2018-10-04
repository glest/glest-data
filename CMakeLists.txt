##################################################################################
# Game data
CMAKE_MINIMUM_REQUIRED( VERSION 3.2.0 )
PROJECT( ZetaGlest )

OPTION(WANT_INSTALL_DATA "Install ZetaGlest's data" OFF)

#
# In this file where the INSTALL() directive is used, nothing is actually installed
# until `make install` is issued. This extra condition isn't really needed, but
# may help prevent overwriting or trying to install data to an existing
# zetaglest data directory.
#
if(WANT_INSTALL_DATA)
	add_definitions("-DDATADIR=${INSTALL_DIR_DATA}")

	IF(NOT INSTALL_DIR_APPDATA)
		SET(INSTALL_DIR_APPDATA "${CMAKE_INSTALL_PREFIX}/share/metainfo/" CACHE PATH "The installation path for appdata files")
	ENDIF()

	IF(NOT INSTALL_DIR_MENU)
		SET(INSTALL_DIR_MENU "${CMAKE_INSTALL_PREFIX}/share/menu/" CACHE PATH "The installation path for menus")
	ENDIF()

	FOREACH(ZG_PATH BIN ICON)
		IF(NOT "${ZETAGLEST_${ZG_PATH}_INSTALL_PATH}" STREQUAL "")
			IF(IS_ABSOLUTE "${ZETAGLEST_${ZG_PATH}_INSTALL_PATH}")
				SET(ZETAGLEST_FULL_${ZG_PATH}_INSTALL_PATH "${ZETAGLEST_${ZG_PATH}_INSTALL_PATH}/")
			ELSE()
				SET(ZETAGLEST_FULL_${ZG_PATH}_INSTALL_PATH "${CMAKE_INSTALL_PREFIX}/${ZETAGLEST_${ZG_PATH}_INSTALL_PATH}/")
			ENDIF()
			STRING(REGEX REPLACE "//+" "/" ZETAGLEST_FULL_${ZG_PATH}_INSTALL_PATH "${ZETAGLEST_FULL_${ZG_PATH}_INSTALL_PATH}")
		ENDIF()
	ENDFOREACH()

	CONFIGURE_FILE("${PROJECT_SOURCE_DIR}/others/menu/zetaglest.menu.in"
		"${PROJECT_BINARY_DIR}/others/menu/zetaglest.menu.in" COPYONLY)
	IF(BUILD_MAP_EDITOR OR NOT DEFINED BUILD_MAP_EDITOR)
		FILE(READ "${PROJECT_SOURCE_DIR}/others/menu/zetaglest_editor.menu.in" EDITOR_MENU)
		FILE(APPEND "${PROJECT_BINARY_DIR}/others/menu/zetaglest.menu.in" "${EDITOR_MENU}")
	ENDIF()
	CONFIGURE_FILE("${PROJECT_BINARY_DIR}/others/menu/zetaglest.menu.in"
		"${PROJECT_BINARY_DIR}/others/menu/zetaglest")

	# Installation of the data
	INSTALL(DIRECTORY "${PROJECT_SOURCE_DIR}/data"
			"${PROJECT_SOURCE_DIR}/docs"
			"${PROJECT_SOURCE_DIR}/maps"
			"${PROJECT_SOURCE_DIR}/scenarios"
			"${PROJECT_SOURCE_DIR}/techs"
			"${PROJECT_SOURCE_DIR}/tilesets"
			"${PROJECT_SOURCE_DIR}/tutorials"
			DESTINATION ${INSTALL_DIR_DATA}
			OPTIONAL REGEX "/.git" EXCLUDE)

	INSTALL(FILES "${PROJECT_SOURCE_DIR}/others/appdata/zetaglest.appdata.xml"
		DESTINATION ${INSTALL_DIR_APPDATA})

		INSTALL(FILES "${PROJECT_SOURCE_DIR}/others/appdata/zetaglest_editor.appdata.xml"
			DESTINATION ${INSTALL_DIR_APPDATA})

	INSTALL(FILES
		"${PROJECT_BINARY_DIR}/others/menu/zetaglest"
		DESTINATION ${INSTALL_DIR_MENU})

	IF(UNIX AND NOT APPLE)
		INSTALL(FILES
		"${PROJECT_SOURCE_DIR}/others/icons/zetaglest.png"
		"${PROJECT_SOURCE_DIR}/others/icons/zetaglest.xpm"
		DESTINATION ${INSTALL_DIR_ICON})
	ENDIF()

	INSTALL(FILES
		"${PROJECT_SOURCE_DIR}/others/desktop/zetaglest.desktop"
		DESTINATION ${INSTALL_DIR_DESKTOP})

	IF(BUILD_MAP_EDITOR OR NOT DEFINED BUILD_MAP_EDITOR)
		INSTALL(FILES
			"${PROJECT_SOURCE_DIR}/others/desktop/zetaglest_editor.desktop"
			DESTINATION ${INSTALL_DIR_DESKTOP})
	ENDIF()

	INSTALL(FILES
			"${PROJECT_SOURCE_DIR}/others/desktop/zetaglest_g3dviewer.desktop"
			DESTINATION ${INSTALL_DIR_DESKTOP})

ENDIF()
