package com.pslab.moneyapk.network

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * Единая точка создания Retrofit — весь остальной код приложения ходит в
 * сеть только через `RetrofitClient.authApi` (а позже — и другие
 * `*Api`-интерфейсы), не создавая свои экземпляры Retrofit.
 *
 * `object` в Kotlin — это синглтон: он создаётся один раз при первом
 * обращении и живёт всё время работы приложения.
 */
object RetrofitClient {

    // Логирует в Logcat (вкладка Logcat в Android Studio) каждый запрос и
    // ответ целиком — очень удобно при отладке, но НЕ для боевой сборки
    // (в теле ответа может быть токен). Уровень BODY нормален, пока
    // приложение общается только с локальным dev-сервером на 10.0.2.2.
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(ApiConfig.BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val authApi: AuthApi = retrofit.create(AuthApi::class.java)
}
