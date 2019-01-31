##################################################################################
# Game data
CMAKE_MINIMUM_REQUIRED( VERSION 3.2.0 )
PROJECT( Glest )

OPTION(WANT_INSTALL_DATA "Install Glest's data" ON)

#
# In this file where the INSTALL() directive is used, nothing is actually installed
# until `make install` is issued. This extra condition isn't really needed, but
# may help prevent overwriting or trying to install data to an existing
# glest data directory.
#
if(WANT_INSTALL_DATA)
	add_definitions("-DDATADIR=${INSTALL_DIR_DATA}")

# The two variables need to be set here, they are not set in the source
# CMakeLists.txt, nor do they need to be.
	IF(NOT INSTALL_DIR_APPDATA)
		SET(INSTALL_DIR_APPDATA "${CMAKE_INSTALL_PREFIX}/share/metainfo/" CACHE PATH "The installation path for appdata files")
	ENDIF()

	IF(NOT INSTALL_DIR_MENU)
		SET(INSTALL_DIR_MENU "${CMAKE_INSTALL_PREFIX}/share/menu/" CACHE PATH "The installation path for menus")
	ENDIF()

	CONFIGURE_FILE("${PROJECT_SOURCE_DIR}/others/menu/glest.menu.in"
		"${PROJECT_BINARY_DIR}/others/menu/glest.menu.in" COPYONLY)
	IF(BUILD_MAP_EDITOR)
		FILE(READ "${PROJECT_SOURCE_DIR}/others/menu/glest_editor.menu.in" EDITOR_MENU)
		FILE(APPEND "${PROJECT_BINARY_DIR}/others/menu/glest.menu.in" "${EDITOR_MENU}")
	ENDIF()
	CONFIGURE_FILE("${PROJECT_BINARY_DIR}/others/menu/glest.menu.in"
		"${PROJECT_BINARY_DIR}/others/menu/glest")

	# Installation of the data
	INSTALL(DIRECTORY "${PROJECT_SOURCE_DIR}/data"
			"${PROJECT_SOURCE_DIR}/docs"
			"${PROJECT_SOURCE_DIR}/maps"
			"${PROJECT_SOURCE_DIR}/scenarios"
			"${PROJECT_SOURCE_DIR}/techs"
			"${PROJECT_SOURCE_DIR}/tilesets"
			"${PROJECT_SOURCE_DIR}/tutorials"
			DESTINATION ${INSTALL_DIR_DATA})

	INSTALL(FILES "${PROJECT_SOURCE_DIR}/others/appdata/glest.appdata.xml"
		DESTINATION ${INSTALL_DIR_APPDATA})

		INSTALL(FILES "${PROJECT_SOURCE_DIR}/others/appdata/glest_editor.appdata.xml"
			DESTINATION ${INSTALL_DIR_APPDATA})

	INSTALL(FILES
		"${PROJECT_BINARY_DIR}/others/menu/glest"
		DESTINATION ${INSTALL_DIR_MENU})

	IF(UNIX AND NOT APPLE)
		INSTALL(FILES
		"${PROJECT_SOURCE_DIR}/others/icons/glest.png"
		"${PROJECT_SOURCE_DIR}/others/icons/glest.xpm"
		DESTINATION ${INSTALL_DIR_ICON})
	ENDIF()

	INSTALL(FILES
		"${PROJECT_SOURCE_DIR}/others/desktop/glest.desktop"
		DESTINATION ${INSTALL_DIR_DESKTOP})

	# Install only the desktop file. The icon gets installed from the
	# cmake file in source/map_editor
	IF(BUILD_MAP_EDITOR)
		INSTALL(FILES
			"${PROJECT_SOURCE_DIR}/others/desktop/glest_editor.desktop"
			DESTINATION ${INSTALL_DIR_DESKTOP})
	ENDIF()

	IF(BUILD_MODEL_VIEWER)
	INSTALL(FILES
			"${PROJECT_SOURCE_DIR}/others/desktop/glest_g3dviewer.desktop"
			DESTINATION ${INSTALL_DIR_DESKTOP})
	ENDIF()

ENDIF()
