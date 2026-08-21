package com.pslab.moneyapk.network

import android.content.Context
import com.google.gson.Gson
import com.pslab.moneyapk.data.TokenStore
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

/**
 * Единая точка создания Retrofit — весь остальной код приложения ходит в
 * сеть только через `RetrofitClient.authApi`/`transactionApi`/`categoryApi`/`reportApi`/
 * `importSessionApi`, не создавая свои экземпляры Retrofit.
 *
 * `object` в Kotlin — это синглтон: он создаётся один раз при первом
 * обращении и живёт всё время работы приложения.
 *
 * Начиная с шага 3 фазы 4 клиенту нужен контекст (чтобы создать [TokenStore]
 * для [AuthInterceptor] — тот сам подставляет сохранённый JWT-токен в каждый
 * запрос). Поэтому появился явный [init] — его вызывает
 * [com.pslab.moneyapk.MoneyApkApplication.onCreate] один раз при старте
 * приложения, раньше любого обращения к `*Api`.
 */
object RetrofitClient {

    private lateinit var tokenStore: TokenStore

    fun init(context: Context) {
        tokenStore = TokenStore(context.applicationContext)
    }

    // Логирует в Logcat (вкладка Logcat в Android Studio) каждый запрос и
    // ответ целиком — очень удобно при отладке, но НЕ для боевой сборки
    // (в теле ответа может быть токен). Уровень BODY нормален, пока
    // приложение общается только с локальным dev-сервером.
    // Добавлен ДО AuthInterceptor, поэтому логирует запрос без заголовка
    // Authorization — токен не попадает в Logcat.
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor(loggingInterceptor)
            .addInterceptor(AuthInterceptor(tokenStore))
            .build()
    }

    /**
     * Общий на весь клиент экземпляр Gson — не только для конвертера Retrofit,
     * но и для ручного разбора тела ответа на 422 у `POST /api/v1/import-sessions`
     * (см. ImportUploadViewModel): Retrofit кладёт тело неуспешного ответа в
     * `response.errorBody()`, а не в `response.body()`, и сам его не парсит.
     * Используя тот же Gson, что и конвертер, не заводим второй источник
     * настроек сериализации.
     */
    val gson: Gson by lazy { Gson() }

    private val retrofit by lazy {
        Retrofit.Builder()
            .baseUrl(ApiConfig.BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
    }

    val authApi: AuthApi by lazy { retrofit.create(AuthApi::class.java) }
    val transactionApi: TransactionApi by lazy { retrofit.create(TransactionApi::class.java) }
    val categoryApi: CategoryApi by lazy { retrofit.create(CategoryApi::class.java) }
    val reportApi: ReportApi by lazy { retrofit.create(ReportApi::class.java) }
    val importSessionApi: ImportSessionApi by lazy { retrofit.create(ImportSessionApi::class.java) }
}
