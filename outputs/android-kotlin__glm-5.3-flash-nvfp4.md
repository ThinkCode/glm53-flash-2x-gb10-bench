# android-kotlin / glm-5.3-flash-nvfp4

- decode 37.7 tok/s
- TTFT 0.26s
- wall 27.4s
- 1024 tokens generated

---

# Paginated List with Jetpack Compose, Hilt, and Retrofit

Below is a complete, production-style implementation using the **Paging 3 library** with Hilt injection, a ViewModel exposing `StateFlow`, a Repository backed by Retrofit, and full loading/error/empty state handling in Compose.

---

## 1. Gradle Dependencies

```kotlin
// build.gradle.kts (app module)
dependencies {
    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.06.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")

    // Lifecycle + ViewModel
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.4")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.4")

    // Paging 3
    implementation("androidx.paging:paging-runtime-ktx:3.3.2")
    implementation("androidx.paging:paging-compose:3.3.2")

    // Retrofit + OkHttp + Moshi
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")

    // Hilt
    implementation("com.google.dagger:hilt-android:2.51.1")
    kapt("com.google.dagger:hilt-compiler:2.51.1")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")
}
```

---

## 2. Data Models

```kotlin
// data/model/User.kt
package com.example.demo.data.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class User(
    val id: Int,
    val name: String,
    val email: String,
    @Json(name = "avatar_url") val avatarUrl: String?
)

@JsonClass(generateAdapter = true)
data class UserResponse(
    val page: Int,
    @Json(name = "per_page") val perPage: Int,
    val total: Int,
    @Json(name = "total_pages") val totalPages: Int,
    val data: List<User>
)
```

---

## 3. Retrofit API Service

```kotlin
// data/remote/UserApiService.kt
package com.example.demo.data.remote

import com.example.demo.data.model.UserResponse
import retrofit2.http.GET
import retrofit2.http.Query

interface UserApiService {
    @GET("api/users")
    suspend fun getUsers(
        @Query("page") page: Int,
        @Query("per_page") perPage: Int = 20
    ): UserResponse
}
```

---

## 4. Repository with Paging Source

```kotlin
// data/repository/UserPagingSource.kt
package com.example.demo.data.repository

import android.util.Log
import androidx.paging.PagingSource
import androidx.paging.PagingState
import com.example.demo.data.model.User
import com.example.demo.data.remote.UserApiService

private const val STARTING_PAGE = 1
private const val PAGE_SIZE = 20

class UserPagingSource(
    private val api: UserApiService
) : PagingSource<Int, User>() {

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, User> {
        val page = params.key ?: STARTING_PAGE
        return try {
            val response = api.getUsers(page = page, perPage = PAGE_SIZE)
            val users = response.data

            LoadResult.Page(
                data = users,
                prevKey = if (page == STARTING_PAGE) null else page - 1,
                nextKey = if (page >= response.totalPages) null else page + 1
            )
        } catch (e: Exception) {
            Log.e("UserPagingSource", "Load failed for page $page", e)
            LoadResult.Error(e)
        }
    }

    override fun getRefreshKey(state: PagingState<Int, User>): Int? {
        return state.anchorPosition?.let { anchor ->
            state.closestPageToPosition(anchor)?.prevKey?.plus(1)
                ?: state.closestPageToPosition(anchor)?.nextKey?.minus(1)
        }
    }
}
```

```kotlin
// data/repository/UserRepository.kt
package com.example.demo.data.repository

import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import com.example.demo.data.model.User
import com.example.demo.data.remote.UserApiService
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@
