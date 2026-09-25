import { Routes } from '@angular/router';
import { CompanyDnaComponent } from './pages/company-dna/company-dna.component';
import { SymbolMatchesComponent } from './pages/symbol-matches/symbol-matches.component';
import { ClientExtraitComponent } from './pages/client-extrait/client-extrait.component';
import { AdminComponent } from './pages/admin/admin.component';
import { LoginComponent } from './pages/login/login.component';
import { ProfileComponent } from './pages/profile/profile.component';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', redirectTo: 'dna', pathMatch: 'full' },
  { path: 'dna', component: CompanyDnaComponent, canActivate: [authGuard] },
  { path: 'matches', component: SymbolMatchesComponent, canActivate: [authGuard] },
  { path: 'extrait', component: ClientExtraitComponent, canActivate: [authGuard] },
  { path: 'admin', component: AdminComponent, canActivate: [authGuard] },
  { path: 'profile', component: ProfileComponent, canActivate: [authGuard] },
  { path: '**', redirectTo: 'dna' },
];
