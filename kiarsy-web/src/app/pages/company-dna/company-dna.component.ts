import { Component, OnInit, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Company } from '../../services/api.service';
import { Chart, RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';

Chart.register(RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

@Component({
  selector: 'app-company-dna',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './company-dna.component.html',
  styleUrl: './company-dna.component.scss',
})
export class CompanyDnaComponent implements OnInit {
  @ViewChild('radarCanvas') radarCanvas?: ElementRef<HTMLCanvasElement>;

  companies: Company[] = [];
  selected: Company | null = null;
  values: any[] = [];
  dimensions: any[] = [];
  matches: any[] = [];
  loading = false;
  error = '';
  private chart?: Chart;

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
    this.dimensions = [];
    this.matches = [];

    this.api.getCompanyValues(c.company_id).subscribe({
      next: (res: any) => (this.values = res.values || []),
    });

    this.api.getCompanyMatches(c.company_id).subscribe({
      next: (res: any) => (this.matches = (res.matches || []).slice(0, 3)),
    });

    this.api.getCompanyDimensions(c.company_id).subscribe({
      next: (res: any) => {
        this.dimensions = res.dimensions || [];
        this.loading = false;
        setTimeout(() => this.renderRadar(), 0);
      },
      error: () => (this.loading = false),
    });
  }

  get topMatchName(): string {
    return this.matches[0]?.symbol_name || '—';
  }

  private renderRadar() {
    if (!this.radarCanvas || this.dimensions.length === 0) return;

    const labels = this.dimensions.map((d) => d.dimension_name);
    const data = this.dimensions.map((d) => Number(d.final_position) || 0);

    if (this.chart) {
      this.chart.destroy();
    }

    this.chart = new Chart(this.radarCanvas.nativeElement, {
      type: 'radar',
      data: {
        labels,
        datasets: [
          {
            label: this.selected?.company_name || 'Company',
            data,
            fill: true,
            backgroundColor: 'rgba(225, 29, 72, 0.25)',
            borderColor: 'rgba(225, 29, 72, 0.9)',
            pointBackgroundColor: 'rgba(225, 29, 72, 1)',
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
        },
        scales: {
          r: {
            min: 0,
            max: 1,
            ticks: { display: false },
            pointLabels: {
              font: { size: 10 },
              color: '#57534e',
            },
            grid: { color: 'rgba(0,0,0,0.06)' },
          },
        },
      },
    });
  }
}
