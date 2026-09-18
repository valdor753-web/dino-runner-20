[app]
title = Dino Runner 2.0
package.name = dinorunner20
package.domain = com.dinorunner.ultimate
source.dir = .
source.include_exts = py,png,jpg,jfif,json,txt
source.include_patterns = img/*,img/dino/*,img/fondo/*
version = 1.0
requirements = python3,kivy,pillow
orientation = landscape
fullscreen = 1

[buildozer]
log_level = 2

[app:android]
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 24
android.ndk = 27b
android.sdk = 33
android.build_tools_version = 33.0.2
android.accept_sdk_license = True
android.archs = arm64-v8a
p4a.bootstrap = sdl2
orientation = landscape

# Icono si tienes uno en img/
# icon.filename = %(source.dir)s/img/dino/correr1.png
# presplash.filename = %(source.dir)s/img/fondo/fondo1.png
