import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SymbolMatchesComponent } from './symbol-matches.component';

describe('SymbolMatchesComponent', () => {
  let component: SymbolMatchesComponent;
  let fixture: ComponentFixture<SymbolMatchesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SymbolMatchesComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SymbolMatchesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
