# ios-swift / glm-5.3-flash-nvfp4

- decode 38.1 tok/s
- TTFT 0.86s
- wall 27.7s
- 1024 tokens generated

---

# SwiftUI Login Screen — Production Quality

Here's a complete, production-ready implementation with proper separation of concerns, validation, error handling, and accessibility support.

## Project Structure

```
Login/
├── Models/
│   └── AuthModels.swift
├── Services/
│   └── AuthService.swift
├── ViewModels/
│   └── LoginViewModel.swift
├── Views/
│   ├── LoginView.swift
│   └── Components/
│       ├── PrimaryButtonStyle.swift
│       └── ValidatedTextField.swift
└── LoginApp.swift
```

---

## 1. Models — `AuthModels.swift`

```swift
import Foundation

// MARK: - Request / Response Models

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct LoginResponse: Decodable {
    let accessToken: String
    let refreshToken: String
    let user: User
}

struct User: Decodable, Identifiable {
    let id: UUID
    let email: String
    let displayName: String
}

// MARK: - Errors

enum AuthError: LocalizedError, Equatable {
    case invalidCredentials
    case networkUnavailable
    case serverError(statusCode: Int)
    case accountLocked
    case unknown

    var errorDescription: String? {
        switch self {
        case .invalidCredentials:
            return "Incorrect email or password. Please try again."
        case .networkUnavailable:
            return "No internet connection. Check your network and try again."
        case .serverError(let code):
            return "Server error (\(code)). Please try again later."
        case .accountLocked:
            return "Your account has been locked. Contact support for help."
        case .unknown:
            return "Something went wrong. Please try again."
        }
    }
}
```

---

## 2. Service Layer — `AuthService.swift`

```swift
import Foundation

// MARK: - Protocol (enables testing/mocking)

protocol AuthServicing {
    func login(email: String, password: String) async throws -> LoginResponse
}

// MARK: - Implementation

final class AuthService: AuthServicing {

    private let session: URLSession
    private let baseURL: URL

    init(session: URLSession = .shared, baseURL: URL) {
        self.session = session
        self.baseURL = baseURL
    }

    func login(email: String, password: String) async throws -> LoginResponse {
        var request = URLRequest(url: baseURL.appendingPathComponent("auth/login"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 15

        do {
            request.httpBody = try JSONEncoder().encode(
                LoginRequest(email: email, password: password)
            )
        } catch {
            throw AuthError.unknown
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw AuthError.unknown
        }

        switch httpResponse.statusCode {
        case 200...299:
            do {
                return try JSONDecoder().decode(LoginResponse.self, from: data)
            } catch {
                throw AuthError.unknown
            }
        case 401, 403:
            throw AuthError.invalidCredentials
        case 423:
            throw AuthError.accountLocked
        case 500...599:
            throw AuthError.serverError(statusCode: httpResponse.statusCode)
        default:
            throw AuthError.unknown
        }
    }
}
```

---

## 3. Validation — `EmailValidator.swift`

```swift
import Foundation

enum EmailValidator {
    /// RFC-5322-lite: pragmatic pattern that catches real-world mistakes
    /// without rejecting valid addresses.
    private static let pattern = #"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"#

    static func isValid(_ email: String) -> Bool {
        email.range(of: pattern, options: .regularExpression) != nil
    }
}

enum PasswordValidator {
    static let minimumLength = 8

    static func validate(_ password: String) -> String? {
        if password.isEmpty { return "Password is required." }
        if password.count < minimumLength {
            return "Password must be at least \(minimumLength) characters."
        }
        return nil
    }
}
```

---

## 4. View Model — `LoginViewModel.swift`

```swift
import Foundation
import Combine

@MainActor
final class LoginViewModel: ObservableObject {

    // MARK: - Input

    @Published var email: String = "" {
        didSet { emailError = validateEmail(email) }
    }
    @Published var password: String = "" {
        didSet { passwordError = PasswordValidator.validate(password) }
    }

    // MARK: -
