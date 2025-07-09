describe('Followers Page with Real Data', () => {
  beforeEach(() => {
    // Mock authentication
    window.localStorage.setItem('authToken', 'mock-jwt-token');
    
    // Mock API responses
    cy.intercept('GET', '**/api/v1/followers', {
      statusCode: 200,
      body: [
        {
          id: 'follower1',
          email: 'trader1@example.com',
          iban: 'DE89370400440532013000',
          commission_pct: 20,
          enabled: true,
          active_positions: 3,
        },
        {
          id: 'follower2',
          email: 'trader2@example.com',
          iban: 'GB82WEST12345698765432',
          commission_pct: 15,
          enabled: false,
          active_positions: 0,
        },
        {
          id: 'follower3',
          email: 'trader3@example.com',
          iban: 'FR1420041010050500013M02606',
          commission_pct: 25,
          enabled: true,
          active_positions: 1,
        },
      ],
    }).as('getFollowers');

    cy.intercept('GET', '**/api/v1/pnl/today', {
      statusCode: 200,
      body: [
        { follower_id: 'follower1', pnl: 1500.50 },
        { follower_id: 'follower2', pnl: -200.75 },
        { follower_id: 'follower3', pnl: 0 },
      ],
    }).as('getPnlToday');

    cy.intercept('GET', '**/api/v1/pnl/month', {
      statusCode: 200,
      body: [
        { follower_id: 'follower1', pnl: 5200.25 },
        { follower_id: 'follower2', pnl: -800.00 },
        { follower_id: 'follower3', pnl: 1200.50 },
      ],
    }).as('getPnlMonth');

    cy.intercept('GET', '**/api/v1/time-value/follower1', {
      statusCode: 200,
      body: {
        follower_id: 'follower1',
        time_value: 2.50,
        status: 'SAFE',
        positions: [
          { symbol: 'QQQ', expiration: '2025-07-20', time_value: 1.25 },
          { symbol: 'SPY', expiration: '2025-07-18', time_value: 1.25 },
        ],
      },
    }).as('getTimeValue1');

    cy.intercept('GET', '**/api/v1/time-value/follower2', {
      statusCode: 200,
      body: {
        follower_id: 'follower2',
        time_value: 0.50,
        status: 'RISK',
        positions: [],
      },
    }).as('getTimeValue2');

    cy.intercept('GET', '**/api/v1/time-value/follower3', {
      statusCode: 200,
      body: {
        follower_id: 'follower3',
        time_value: 0.08,
        status: 'CRITICAL',
        positions: [
          { symbol: 'TQQQ', expiration: '2025-07-11', time_value: 0.08 },
        ],
      },
    }).as('getTimeValue3');

    cy.intercept('GET', '**/api/v1/health', {
      statusCode: 200,
      body: {
        overall_status: 'GREEN',
        timestamp: new Date().toISOString(),
        database: {
          status: 'healthy',
          type: 'mongodb',
        },
        system: {
          cpu_percent: 45.5,
          memory_percent: 60.2,
          disk_percent: 70.8,
          status: 'healthy',
        },
        services: [
          {
            name: 'trading-bot',
            status: 'healthy',
            response_time_ms: 150,
            critical: true,
          },
          {
            name: 'watchdog',
            status: 'unhealthy',
            response_time_ms: 5000,
            critical: false,
          },
        ],
      },
    }).as('getHealth');

    cy.visit('/followers');
  });

  it('displays followers with real data', () => {
    cy.wait(['@getFollowers', '@getPnlToday', '@getPnlMonth']);
    
    // Check that followers are displayed
    cy.get('[data-testid="DataGrid-root"]').should('exist');
    cy.contains('follower1').should('be.visible');
    cy.contains('follower2').should('be.visible');
    cy.contains('follower3').should('be.visible');
  });

  it('displays P&L data correctly', () => {
    cy.wait(['@getFollowers', '@getPnlToday', '@getPnlMonth']);
    
    // Check P&L Today column
    cy.contains('+$1,500.50').should('be.visible');
    cy.contains('-$200.75').should('be.visible');
    cy.contains('+$0.00').should('be.visible');
    
    // Check P&L Month column
    cy.contains('+$5,200.25').should('be.visible');
    cy.contains('-$800.00').should('be.visible');
    cy.contains('+$1,200.50').should('be.visible');
  });

  it('displays time value badges with correct colors', () => {
    cy.wait(['@getTimeValue1', '@getTimeValue2', '@getTimeValue3']);
    
    // Check SAFE badge (green)
    cy.contains('TV: $2.50')
      .should('be.visible')
      .parent()
      .should('have.css', 'color')
      .and('match', /rgb\(.*green.*/i);
    
    // Check RISK badge (yellow)
    cy.contains('TV: $0.50')
      .should('be.visible')
      .parent()
      .should('have.css', 'color')
      .and('match', /rgb\(.*yellow.*/i);
    
    // Check CRITICAL badge (red)
    cy.contains('TV: $0.08')
      .should('be.visible')
      .parent()
      .should('have.css', 'color')
      .and('match', /rgb\(.*red.*/i);
  });

  it('displays health status indicator', () => {
    cy.wait('@getHealth');
    
    // Check for health dot
    cy.get('[data-testid="FiberManualRecordIcon"]').should('exist');
  });

  it('shows service restart menu', () => {
    cy.wait('@getHealth');
    
    // Click on refresh button
    cy.get('[data-testid="RefreshIcon"]').parent().click();
    
    // Check menu items
    cy.contains('Restart trading-bot').should('be.visible');
    cy.contains('Restart watchdog').should('be.visible');
  });

  it('handles service restart action', () => {
    cy.intercept('POST', '**/api/v1/service/trading-bot/restart', {
      statusCode: 200,
      body: { success: true },
    }).as('restartService');
    
    cy.wait('@getHealth');
    
    // Click on refresh button
    cy.get('[data-testid="RefreshIcon"]').parent().click();
    
    // Click restart trading-bot
    cy.contains('Restart trading-bot').click();
    
    // Verify API call
    cy.wait('@restartService');
  });

  it('handles follower actions', () => {
    cy.wait(['@getFollowers']);
    
    // Click more actions on first follower
    cy.get('[data-testid="MoreVertIcon"]').first().click();
    
    // Check menu options
    cy.contains('View Trades').should('be.visible');
    cy.contains('View Logs').should('be.visible');
    cy.contains('Disable').should('be.visible');
    cy.contains('Close Positions').should('be.visible');
  });

  it('handles close positions with PIN', () => {
    cy.intercept('POST', '**/api/v1/manual-close', {
      statusCode: 200,
      body: { success: true },
    }).as('closePositions');
    
    cy.wait(['@getFollowers']);
    
    // Click more actions on first follower
    cy.get('[data-testid="MoreVertIcon"]').first().click();
    
    // Click close positions
    cy.contains('Close Positions').click();
    
    // Confirm dialog should appear
    cy.contains('Confirm Action').should('be.visible');
    
    // Enter PIN
    cy.get('input[type="password"]').type('0312');
    
    // Click confirm
    cy.contains('button', 'Confirm close positions').click();
    
    // Verify API call
    cy.wait('@closePositions').then((interception) => {
      expect(interception.request.body).to.deep.include({
        follower_id: 'follower1',
        pin: '0312',
        close_all: true,
      });
    });
  });

  it('polls health status every 15 seconds', () => {
    let healthCallCount = 0;
    
    cy.intercept('GET', '**/api/v1/health', (req) => {
      healthCallCount++;
      req.reply({
        statusCode: 200,
        body: {
          overall_status: healthCallCount === 1 ? 'GREEN' : 'YELLOW',
          timestamp: new Date().toISOString(),
          database: { status: 'healthy', type: 'mongodb' },
          system: {
            cpu_percent: 45.5,
            memory_percent: 60.2,
            disk_percent: 70.8,
            status: 'healthy',
          },
          services: [],
        },
      });
    }).as('getHealthPolling');
    
    // Initial health check
    cy.wait('@getHealthPolling');
    
    // Wait for polling interval (using shorter time for test)
    cy.clock();
    cy.tick(15000);
    
    // Should make another health check
    cy.wait('@getHealthPolling');
  });

  it('handles follower expansion', () => {
    cy.wait(['@getFollowers']);
    
    // Click expand button on first follower
    cy.get('[data-testid="ExpandMoreIcon"]').first().click();
    
    // Check expanded content
    cy.contains('ACCOUNT DETAILS').should('be.visible');
    cy.contains('TIME VALUE').should('be.visible');
    cy.contains('PERFORMANCE').should('be.visible');
    
    // Check follower details
    cy.contains('Email: trader1@example.com').should('be.visible');
    cy.contains('IBAN: DE89370400440532013000').should('be.visible');
    cy.contains('Commission: 20%').should('be.visible');
  });
});