// Корневой build-файл: только объявление плагинов (apply false) — сами плагины
// подключаются в модулях (см. app/build.gradle.kts).
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.compose.compiler) apply false
}
