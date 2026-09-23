import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Company } from '../../services/api.service';

@Component({
  selector: 'app-symbol-matches',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './symbol-matches.component.html',
  styleUrl: './symbol-matches.component.scss',
})
export class SymbolMatchesComponent implements OnInit {
  companies: Company[] = [];
  selected: Company | null = null;
  matches: any[] = [];
  loading = false;
  error = '';

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getCompanies().subscribe({
      next: (res) => (this.companies = res.companies),
      error: () =>
        (this.error = 'Cannot reach API. Is python scripts/api_v2.py running?'),
    });
  }

  selectCompany(c: Company) {
    this.selected = c;
    this.loading = true;
    this.matches = [];
    this.api.getCompanyMatches(c.company_id).subscribe({
      next: (res: any) => {
        this.matches = res.matches || [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load matches';
      },
    });
  }

  cultureLabel(id: string): string {
    const map: Record<string, string> = {
      amazigh: 'Amazigh',
      amerindienne: 'Amérindienne',
      subsaharienne: 'Subsaharienne — Akan/Adinkra',
    };
    return map[id] || id;
  }
}
