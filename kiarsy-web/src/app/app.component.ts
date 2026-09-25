import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss',
})
export class AppComponent {
  title = 'Kiarsy Cultural Affinity Engine';

  constructor(public api: ApiService, private router: Router) {}

  get username(): string {
    return localStorage.getItem('kiarsy_username') || '';
  }

  logout() {
    this.api.logout();
    this.router.navigateByUrl('/login');
  }
}
