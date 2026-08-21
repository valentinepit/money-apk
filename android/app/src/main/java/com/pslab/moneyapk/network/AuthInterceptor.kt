package com.pslab.moneyapk.network

import com.pslab.moneyapk.data.TokenStore
import okhttp3.Interceptor
import okhttp3.Response

/**
 * OkHttp-перехватчик — вызывается для каждого исходящего запроса. Если в
 * [TokenStore] есть сохранённый JWT-токен, подставляет заголовок
 * `Authorization: Bearer <токен>` — так каждый вызов защищённого эндпоинта
 * (транзакции, категории, отчёты) не должен сам заботиться об авторизации.
 * На вызов логина (когда токена ещё нет) заголовок просто не добавляется —
 * этому эндпоинту авторизация и не требуется.
 */
class AuthInterceptor(private val tokenStore: TokenStore) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val token = tokenStore.getToken()
        return if (token != null) {
            chain.proceed(request.newBuilder().addHeader("Authorization", "Bearer $token").build())
        } else {
            chain.proceed(request)
        }
    }
}
