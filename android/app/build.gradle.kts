plugins {
    id("com.android.application")
}

android {
    namespace = "dev.ajuntanaga.io24"
    compileSdk = 35

    defaultConfig {
        applicationId = "dev.ajuntanaga.io24"
        minSdk = 23
        targetSdk = 35
        versionCode = 9
        versionName = "0.3.4"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    lint {
        abortOnError = true
        checkReleaseBuilds = true
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
