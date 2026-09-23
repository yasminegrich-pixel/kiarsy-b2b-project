import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CompanyDnaComponent } from './company-dna.component';

describe('CompanyDnaComponent', () => {
  let component: CompanyDnaComponent;
  let fixture: ComponentFixture<CompanyDnaComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CompanyDnaComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CompanyDnaComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
