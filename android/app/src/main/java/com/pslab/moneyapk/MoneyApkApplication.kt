package com.pslab.moneyapk

import android.app.Application
import com.pslab.moneyapk.network.RetrofitClient

/**
 * Application-класс — код здесь запускается один раз при старте процесса
 * приложения, раньше первой Activity. Нужен, чтобы один раз инициализировать
 * [RetrofitClient] с контекстом приложения: тому, в свою очередь, нужен
 * контекст, чтобы создать [com.pslab.moneyapk.data.TokenStore] и
 * автоматически подставлять сохранённый JWT-токен во все запросы к API
 * (см. [com.pslab.moneyapk.network.AuthInterceptor]) — без этого пришлось
 * бы вручную передавать токен в каждый вызов *Api.
 */
class MoneyApkApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        RetrofitClient.init(this)
    }
}
