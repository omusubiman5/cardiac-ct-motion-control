"""Run inside 3D Slicer to enable the installed Japanese translation pack."""

import slicer


settings = slicer.app.userSettings()
settings.setValue("Internationalization/Enabled", True)
settings.setValue("language", "ja_JP")
settings.sync()

print("INTERNATIONALIZATION_ENABLED=" + str(settings.value("Internationalization/Enabled")))
print("LANGUAGE=" + str(settings.value("language")))
slicer.util.exit()
