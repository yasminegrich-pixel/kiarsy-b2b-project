import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  username = '';
  password = '';
  error = '';
  info = '';
  loading = false;
  mode: 'login' | 'forgot' = 'login';

  constructor(private api: ApiService, private router: Router) {}

  submitLogin() {
    this.error = '';
    this.info = '';
    this.loading = true;
    this.api.login(this.username, this.password).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigateByUrl('/dna');
      },
      error: () => {
        this.loading = false;
        this.error = 'Invalid username or password';
      },
    });
  }

  submitForgot() {
    this.error = '';
    this.info = '';
    this.loading = true;
    this.api.forgotPassword(this.username).subscribe({
      next: (res) => {
        this.loading = false;
        this.info = res.message;
        this.mode = 'login';
      },
      error: () => {
        this.loading = false;
        this.error = 'Could not process reset request';
      },
    });
  }
}
