# android-kotlin / glm-5.3-flash-exl3

- decode 34.2 tok/s
- TTFT 0.40s
- wall 30.3s
- 1024 tokens generated

---

# Paginated List with Jetpack Compose, Hilt, and Paging 3

Below is a complete, production-style implementation using **Paging 3** (the recommended approach for paginated lists), **Retrofit**, **StateFlow**, and **Hilt**.

## Project Structure

```
data/
  ├── api/UserApi.kt
  ├── model/User.kt
  ├── paging/UserPagingSource.kt
  └── repository/UserRepository.kt
di/
  └── NetworkModule.kt
ui/
  ├── UserListViewModel.kt
  ├── UserListScreen.kt
  └── components/ (composables below)
```

---

## 1. Data Models

```kotlin
// data/model/User.kt
data class User(
    val id: Int,
    val name: String,
    val email: String,
    @SerializedName("avatar_url") val avatarUrl: String?
)

data class UserResponse(
    val page: Int,
    @SerializedName("per_page") val perPage: Int,
    val total: Int,
    @SerializedName("total_pages") val totalPages: Int,
    val data: List<User>
)
```

---

## 2. Retrofit API

```kotlin
// data/api/UserApi.kt
interface UserApi {
    @GET("api/users")
    suspend fun getUsers(
        @Query("page") page: Int,
        @Query("per_page") perPage: Int = 20
    ): UserResponse
}
```

---

## 3. Hilt Network Module

```kotlin
// di/NetworkModule.kt
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            })
            .build()

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit =
        Retrofit.Builder()
            .baseUrl("https://reqres.in/")
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

    @Provides
    @Singleton
    fun provideUserApi(retrofit: Retrofit): UserApi =
        retrofit.create(UserApi::class.java)
}
```

---

## 4. Paging Source

```kotlin
// data/paging/UserPagingSource.kt
class UserPagingSource(
    private val api: UserApi
) : PagingSource<Int, User>() {

    companion object {
        private const val STARTING_PAGE = 1
    }

    override suspend fun load(params: LoadParams<Int>): LoadResult<Int, User> {
        return try {
            val page = params.key ?: STARTING_PAGE
            val response = api.getUsers(page = page)

            LoadResult.Page(
                data = response.data,
                prevKey = if (page == STARTING_PAGE) null else page - 1,
                nextKey = if (page >= response.totalPages) null else page + 1
            )
        } catch (e: IOException) {
            LoadResult.Error(e)
        } catch (e: HttpException) {
            LoadResult.Error(e)
        }
    }

    override fun getRefreshKey(state: PagingState<Int, User>): Int? =
        state.anchorPosition?.let { anchorPosition ->
            state.closestPageToPosition(anchorPosition)?.prevKey?.plus(1)
                ?: state.closestPageToPosition(anchorPosition)?.nextKey?.minus(1)
        }
}
```

---

## 5. Repository

```kotlin
// data/repository/UserRepository.kt
class UserRepository @Inject constructor(
    private val api: UserApi
) {
    fun getUsersPager(): Flow<PagingData<User>> =
        Pager(
            config = PagingConfig(
                pageSize = 20,
                prefetchDistance = 5,
                enablePlaceholders = false,
                initialLoadSize = 20
            ),
            pagingSourceFactory = { UserPagingSource(api) }
        ).flow
}
```

---

## 6. ViewModel with StateFlow

```kotlin
// ui/UserListViewModel.kt
@HiltViewModel
class UserListViewModel @Inject constructor(
    repository: UserRepository
) : ViewModel() {

    val users: StateFlow<UiState> = repository.getUsersPager()
        .cachedIn(viewModelScope)
        .map { pagingData -> UiState.Success(pagingData) as UiState }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = UiState.Loading
        )

    sealed interface UiState {
        data object Loading : UiState
        data class Error(val message: String) : UiState
        data class Success(val paging
