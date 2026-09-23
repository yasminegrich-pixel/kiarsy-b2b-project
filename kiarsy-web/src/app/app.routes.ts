import { Routes } from '@angular/router';
import { CompanyDnaComponent } from './pages/company-dna/company-dna.component';
import { SymbolMatchesComponent } from './pages/symbol-matches/symbol-matches.component';
import { ClientExtraitComponent } from './pages/client-extrait/client-extrait.component';
import { AdminComponent } from './pages/admin/admin.component';

export const routes: Routes = [
  { path: '', redirectTo: 'dna', pathMatch: 'full' },
  { path: 'dna', component: CompanyDnaComponent },
  { path: 'matches', component: SymbolMatchesComponent },
  { path: 'extrait', component: ClientExtraitComponent },
  { path: 'admin', component: AdminComponent },
  { path: '**', redirectTo: 'dna' },
];
