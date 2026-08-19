package com.pslab.moneyapk.network

import retrofit2.Response
import retrofit2.http.Field
import retrofit2.http.FormUrlEncoded
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface TransactionApi {

    /** По умолчанию бэкенд сортирует по дате траты по убыванию (новые сверху). */
    @GET("api/v1/transactions")
    suspend fun listTransactions(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 50
    ): Response<TransactionListResponse>

    /**
     * `category_id` необязателен — если не передать, бэкенд сам поставит
     * системную категорию "Другое" (см. docs/api/api-contract.md, Transactions).
     * `transaction_date` — строка в формате `YYYY-MM-DD`.
     */
    @FormUrlEncoded
    @POST("api/v1/transactions")
    suspend fun createTransaction(
        @Field("amount") amount: Double,
        @Field("transaction_date") transactionDate: String,
        @Field("category_id") categoryId: String? = null,
        @Field("merchant_raw") merchantRaw: String? = null,
        @Field("note") note: String? = null
    ): Response<TransactionDataResponse>
}
