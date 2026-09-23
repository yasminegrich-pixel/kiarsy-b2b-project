import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

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

  constructor(private http: HttpClient) {}

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

  addCulture(body: { culture_id: string; culture_name: string }) {
    return this.http.post(`${this.baseUrl}/cultures`, body);
  }

  addSymbol(body: any) {
    return this.http.post(`${this.baseUrl}/symbols`, body);
  }

  deleteCompany(companyId: string) {
    return this.http.delete(`${this.baseUrl}/companies/${companyId}`);
  }

  listSymbols(cultureId?: string) {
    const q = cultureId ? `?culture_id=${encodeURIComponent(cultureId)}` : '';
    return this.http.get<{ count: number; symbols: any[] }>(
      `${this.baseUrl}/symbols${q}`
    );
  }

  deleteSymbol(symbolId: string) {
    return this.http.delete(`${this.baseUrl}/symbols/${encodeURIComponent(symbolId)}`);
  }

  deleteCulture(cultureId: string) {
    return this.http.delete(`${this.baseUrl}/cultures/${encodeURIComponent(cultureId)}`);
  }

  processCompany(body: {
    company_name: string;
    website_url: string;
    industry?: string;
    region?: string;
  }) {
    return this.http.post(`${this.baseUrl}/companies/process`, body);
  }

}
