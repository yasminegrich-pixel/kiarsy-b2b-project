import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profile.component.html',
  styleUrl: './profile.component.scss',
})

export class ProfileComponent implements OnInit {
  profile = {
    username: '',
    email: '',
    full_name: '',
    role: '',
  };

  currentPassword = '';
  newPassword = '';
  confirmPassword = '';

  message = '';
  error = '';
  loading = false;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getProfile().subscribe({
      next: (res) => {
        this.profile.username = res.username || '';
        this.profile.email = res.email || '';
        this.profile.full_name = res.full_name || '';
        this.profile.role = res.role || '';
      },
      error: () => (this.error = 'Could not load profile. Please log in again.'),
    });
  }

  saveProfile() {
    this.message = '';
    this.error = '';
    this.loading = true;
    this.api
      .updateProfile({
        username: this.profile.username,
        email: this.profile.email,
        full_name: this.profile.full_name,
      })
      .subscribe({
        next: (res) => {
          this.loading = false;
          this.message = res.message || 'Profile updated';
          this.profile.username = res.user.username;
          this.profile.email = res.user.email || '';
          this.profile.full_name = res.user.full_name || '';
        },
        error: (e) => {
          this.loading = false;
          this.error = e.error?.detail || 'Update failed';
        },
      });
  }

  savePassword() {
    this.message = '';
    this.error = '';
    if (this.newPassword.length < 8) {
      this.error = 'New password must be at least 8 characters';
      return;
    }
    if (this.newPassword !== this.confirmPassword) {
      this.error = 'New passwords do not match';
      return;
    }
    this.loading = true;
    this.api.changePassword(this.currentPassword, this.newPassword).subscribe({
      next: (res) => {
        this.loading = false;
        this.message = res.message;
        this.currentPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
      },
      error: (e) => {
        this.loading = false;
        this.error = e.error?.detail || 'Password change failed';
      },
    });
  }
}
