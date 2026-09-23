import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Company } from '../../services/api.service';

@Component({
  selector: 'app-client-extrait',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './client-extrait.component.html',
  styleUrl: './client-extrait.component.scss',
})
export class ClientExtraitComponent implements OnInit {
  companies: Company[] = [];
  selected: Company | null = null;
  values: any[] = [];
  matches: any[] = [];
  dimensions: any[] = [];
  loading = false;
  error = '';
  today = new Date();

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
    this.values = [];
    this.matches = [];
    this.dimensions = [];

    this.api.getCompanyValues(c.company_id).subscribe({
      next: (res: any) => (this.values = res.values || []),
    });

    this.api.getCompanyDimensions(c.company_id).subscribe({
      next: (res: any) => {
        const dims = res.dimensions || [];
        this.dimensions = [...dims]
          .sort((a, b) => Number(b.final_position) - Number(a.final_position))
          .slice(0, 5);
      },
    });

    this.api.getCompanyMatches(c.company_id).subscribe({
      next: (res: any) => {
        this.matches = (res.matches || []).slice(0, 4);
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  valuesByTier(tier: string) {
    return this.values.filter((v) => v.tier === tier);
  }

  print() {
    window.print();
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
