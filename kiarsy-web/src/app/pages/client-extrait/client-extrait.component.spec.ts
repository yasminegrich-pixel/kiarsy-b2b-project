import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ClientExtraitComponent } from './client-extrait.component';

describe('ClientExtraitComponent', () => {
  let component: ClientExtraitComponent;
  let fixture: ComponentFixture<ClientExtraitComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ClientExtraitComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ClientExtraitComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
