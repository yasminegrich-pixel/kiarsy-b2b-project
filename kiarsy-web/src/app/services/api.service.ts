import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

export interface Company {
  company_id: string;
  company_name: string;
  industry?: string;
  country_region?: string;
  websites?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = 'http://127.0.0.1:8000';
  private tokenKey = 'kiarsy_token';

  constructor(private http: HttpClient) {}

  // ---------- auth ----------
  login(username: string, password: string) {
    return this.http
      .post<{ access_token: string; role: string; username: string }>(
        `${this.baseUrl}/auth/login`,
        { username, password }
      )
      .pipe(
        tap((res) => {
          localStorage.setItem(this.tokenKey, res.access_token);
          localStorage.setItem('kiarsy_role', res.role);
          localStorage.setItem('kiarsy_username', res.username);
        })
      );
  }

  listUsers() {
    return this.http.get<{ users: any[] }>(`${this.baseUrl}/users`, {
      headers: this.authHeaders(),
    });
  }

  createUser(body: {
    username: string;
    password: string;
    email?: string;
    full_name?: string;
    role: string;
  }) {
    return this.http.post(`${this.baseUrl}/users`, body, {
      headers: this.authHeaders(),
    });
  }

  deleteUser(userId: number) {
    return this.http.delete(`${this.baseUrl}/users/${userId}`, {
      headers: this.authHeaders(),
    });
  }

  updateUser(
    userId: number,
    body: {
      email?: string;
      full_name?: string;
      role?: string;
      is_active?: boolean;
      password?: string;
    }
  ) {
    return this.http.put(`${this.baseUrl}/users/${userId}`, body, {
      headers: this.authHeaders(),
    });
  }

  logout() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem('kiarsy_role');
    localStorage.removeItem('kiarsy_username');
  }

  getToken(): string | null {
    return localStorage.getItem(this.tokenKey);
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }
 
  forgotPassword(username: string) {
    return this.http.post<{ ok: boolean; message: string }>(
      `${this.baseUrl}/auth/forgot-password`,
      { username }
    );
  }

   getProfile() {
    return this.http.get<any>(`${this.baseUrl}/auth/profile`, {
      headers: this.authHeaders(),
    });
  }

  updateProfile(body: { full_name?: string; email?: string; username?: string }) {
    return this.http.put<{ user: any; access_token: string; message: string }>(
      `${this.baseUrl}/auth/profile`,
      body,
      { headers: this.authHeaders() }
    ).pipe(
      tap((res) => {
        if (res.access_token) {
          localStorage.setItem(this.tokenKey, res.access_token);
        }
        if (res.user?.username) {
          localStorage.setItem('kiarsy_username', res.user.username);
        }
        if (res.user?.role) {
          localStorage.setItem('kiarsy_role', res.user.role);
        }
      })
    );
  }

  changePassword(current_password: string, new_password: string) {
    return this.http.post<{ ok: boolean; message: string }>(
      `${this.baseUrl}/auth/change-password`,
      { current_password, new_password },
      { headers: this.authHeaders() }
    );
  }

  private authHeaders(): HttpHeaders {
    const token = this.getToken();
    return token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
  }

  // ---------- read ----------
  getCompanies(): Observable<{ count: number; companies: Company[] }> {
    return this.http.get<{ count: number; companies: Company[] }>(
      `${this.baseUrl}/companies`
    );
  }

  getCompanyValues(companyId: string) {
    return this.http.get(`${this.baseUrl}/companies/${companyId}/values`);
  }

  getCompanyDimensions(companyId: string) {
    return this.http.get(`${this.baseUrl}/companies/${companyId}/dimensions`);
  }

  getCompanyMatches(companyId: string) {
    return this.http.get(
      `${this.baseUrl}/companies/${companyId}/matches?open_only=true&limit=20`
    );
  }

  getCultures() {
    return this.http.get<{ cultures: { culture_id: string; culture_name: string }[] }>(
      `${this.baseUrl}/cultures`
    );
  }

  listSymbols(cultureId?: string) {
    const q = cultureId ? `?culture_id=${encodeURIComponent(cultureId)}` : '';
    return this.http.get<{ count: number; symbols: any[] }>(
      `${this.baseUrl}/symbols${q}`
    );
  }

  // ---------- write (JWT required) ----------
  addCulture(body: { culture_id: string; culture_name: string }) {
    return this.http.post(`${this.baseUrl}/cultures`, body, {
      headers: this.authHeaders(),
    });
  }

  addSymbol(body: any) {
    return this.http.post(`${this.baseUrl}/symbols`, body, {
      headers: this.authHeaders(),
    });
  }

  deleteCompany(companyId: string) {
    return this.http.delete(`${this.baseUrl}/companies/${companyId}`, {
      headers: this.authHeaders(),
    });
  }

  deleteSymbol(symbolId: string) {
    return this.http.delete(
      `${this.baseUrl}/symbols/${encodeURIComponent(symbolId)}`,
      { headers: this.authHeaders() }
    );
  }

  deleteCulture(cultureId: string) {
    return this.http.delete(
      `${this.baseUrl}/cultures/${encodeURIComponent(cultureId)}`,
      { headers: this.authHeaders() }
    );
  }

  processCompany(body: {
    company_name: string;
    website_url: string;
    industry?: string;
    region?: string;
  }) {
    return this.http.post(`${this.baseUrl}/companies/process`, body, {
      headers: this.authHeaders(),
    });
  }
}
