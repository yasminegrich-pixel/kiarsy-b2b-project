import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Company } from '../../services/api.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.scss',
})
export class AdminComponent implements OnInit {
  companies: Company[] = [];
  cultures: { culture_id: string; culture_name: string }[] = [];
  symbols: any[] = [];
  message = '';
  error = '';
  processing = false;

  // process company
  companyForm = {
    company_name: '',
    website_url: '',
    industry: '',
    region: '',
  };

  users: any[] = [];
  isAdmin = localStorage.getItem('kiarsy_role') === 'admin';

  newUser = {
    username: '',
    password: '',
    email: '',
    full_name: '',
    role: 'viewer',
  };

  deleteId = '';
  newCultureId = '';
  newCultureName = '';
  deleteCultureId = '';
  filterCultureId = '';
  deleteSymbolId = '';

  symbol = {
    symbol_id: '',
    symbol_name: '',
    culture_id: '',
    documented_meaning: '',
    sources: '',
    source_url: '',
    verification_level: 'verified_candidate',
    usage_status: 'open',
    usage_note: '',
  };

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.reload();
  }

  reload() {
    this.api.getCompanies().subscribe({ next: (r) => (this.companies = r.companies) });
    this.api.getCultures().subscribe({ next: (r) => (this.cultures = r.cultures) });
    this.loadSymbols();
    if (this.isAdmin) {
      this.api.listUsers().subscribe({
        next: (r) => (this.users = r.users || []),
        error: () => (this.users = []),
      });
    }
  }

  loadSymbols() {
    this.api.listSymbols(this.filterCultureId || undefined).subscribe({
      next: (r) => (this.symbols = r.symbols),
    });
  }

  processCompany() {
    this.message = '';
    this.error = '';
    this.processing = true;
    this.api.processCompany(this.companyForm).subscribe({
      next: (res: any) => {
        this.processing = false;
        this.message = res.message || 'Company processed successfully.';
        this.companyForm = { company_name: '', website_url: '', industry: '', region: '' };
        this.reload();
      },
      error: (e) => {
        this.processing = false;
        this.error = e.error?.detail || 'Processing failed';
      },
    });
  }

  createCulture() {
    this.message = '';
    this.error = '';
    this.api.addCulture({ culture_id: this.newCultureId, culture_name: this.newCultureName }).subscribe({
      next: () => {
        this.message = 'Culture added.';
        this.newCultureId = '';
        this.newCultureName = '';
        this.reload();
      },
      error: (e) => (this.error = e.error?.detail || 'Failed to add culture'),
    });
  }

  removeCulture() {
    if (!this.deleteCultureId) return;
    if (!confirm('Delete this culture? It must have zero symbols.')) return;
    this.api.deleteCulture(this.deleteCultureId).subscribe({
      next: () => {
        this.message = 'Culture deleted.';
        this.deleteCultureId = '';
        this.reload();
      },
      error: (e) => (this.error = e.error?.detail || 'Failed to delete culture'),
    });
  }

  createSymbol() {
    this.message = '';
    this.error = '';
    this.api.addSymbol(this.symbol).subscribe({
      next: (res: any) => {
        this.message = res.note || 'Symbol saved.';
        this.symbol.symbol_id = '';
        this.symbol.symbol_name = '';
        this.symbol.documented_meaning = '';
        this.symbol.usage_note = '';
        this.loadSymbols();
      },
      error: (e) => (this.error = e.error?.detail || 'Failed to add symbol'),
    });
  }

  removeSymbol() {
    if (!this.deleteSymbolId) return;
    if (!confirm('Delete this symbol and its scores/matches?')) return;
    this.api.deleteSymbol(this.deleteSymbolId).subscribe({
      next: () => {
        this.message = 'Symbol deleted.';
        this.deleteSymbolId = '';
        this.loadSymbols();
      },
      error: (e) => (this.error = e.error?.detail || 'Failed to delete symbol'),
    });
  }

  removeCompany() {
    if (!this.deleteId) return;
    if (!confirm('Delete this company and all its scores/matches?')) return;
    this.api.deleteCompany(this.deleteId).subscribe({
      next: () => {
        this.message = 'Company deleted.';
        this.deleteId = '';
        this.reload();
      },
      error: (e) => (this.error = e.error?.detail || 'Delete failed'),
    });
  }

  createUserAccount() {
    this.message = '';
    this.error = '';
    this.api.createUser(this.newUser).subscribe({
      next: () => {
        this.message = 'User created.';
        this.newUser = {
          username: '',
          password: '',
          email: '',
          full_name: '',
          role: 'viewer',
        };
        this.reload();
      },
      error: (e) => (this.error = e.error?.detail || 'Could not create user'),
    });
  }

  setUserRole(u: any, role: string) {
    this.api.updateUser(u.user_id, { role }).subscribe({
      next: () => {
        this.message = `Role updated for ${u.username}`;
        this.reload();
      },
      error: (e) => (this.error = e.error?.detail || 'Role update failed'),
    });
  }

  toggleUserActive(u: any) {
    this.api.updateUser(u.user_id, { is_active: !u.is_active }).subscribe({
      next: () => {
        this.message = `${u.username} ${!u.is_active ? 'activated' : 'deactivated'}`;
        this.reload();
      },
      error: (e) => (this.error = e.error?.detail || 'Update failed'),
    });
  }

  deleteUserAccount(u: any) {
    if (u.username === localStorage.getItem('kiarsy_username')) {
      this.error = 'You cannot delete your own account';
      return;
    }
    if (!confirm(`Permanently delete user "${u.username}"? This cannot be undone.`)) {
      return;
    }
    this.api.deleteUser(u.user_id).subscribe({
      next: () => {
        this.message = `User ${u.username} deleted.`;
        this.reload();
      },
      error: (e) => (this.error = e.error?.detail || 'Delete failed'),
    });
  }

}

