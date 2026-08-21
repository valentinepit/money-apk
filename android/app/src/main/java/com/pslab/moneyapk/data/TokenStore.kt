package com.pslab.moneyapk.data

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Хранилище JWT-токена на диске телефона.
 *
 * Используем [EncryptedSharedPreferences] — обычные SharedPreferences (простой
 * набор ключ-значение), но файл на диске физически зашифрован. Google в 2025
 * пометил этот класс как deprecated в пользу более нового подхода (DataStore +
 * Tink-шифрование), но EncryptedSharedPreferences по-прежнему работает и
 * остаётся разумным выбором для личного некоммерческого приложения — сюда
 * можно будет вернуться и мигрировать позже, если понадобится.
 *
 * [MasterKey] — это ключ шифрования, который Android хранит в защищённом
 * аппаратном хранилище устройства (Android Keystore), а не в файле рядом с
 * данными — поэтому просто скопировать файл с токеном на другое устройство
 * не получится.
 */
class TokenStore(context: Context) {

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "auth_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun saveToken(token: String) {
        prefs.edit().putString(KEY_TOKEN, token).apply()
    }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)

    fun clearToken() {
        prefs.edit().remove(KEY_TOKEN).apply()
    }

    private companion object {
        const val KEY_TOKEN = "jwt_token"
    }
}
