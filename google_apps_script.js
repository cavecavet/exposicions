// Google Apps Script for FotosCavet Card Management
// Handles user authentication, card adoption, and card data storage
//
// Users sheet columns: A=Name, B=Username, C=Password, D=DisplayName, E=AdoptedCard
// Cards sheet columns: A=CardID, B=PhotoID, C=CommonName, D=ScientificName, E=Comment, F=FotoAuthor, G=CardAuthor, H=LastModified

// Pre-defined card-to-photo mappings (used to seed the Cards sheet)
const CARD_SEED_DATA = [
  { cardId: '01FC05', photoId: 'FotosCavet00005' },
  { cardId: '02FC08', photoId: 'FotosCavet00008' },
  { cardId: '03FC12', photoId: 'FotosCavet00012' },
  { cardId: '04FC15', photoId: 'FotosCavet00015' },
  { cardId: '05FC06', photoId: 'FotosCavet00006' },
  { cardId: '06FC04', photoId: 'FotosCavet00004' },
  { cardId: '07FC02', photoId: 'FotosCavet00002' },
  { cardId: '08FC07', photoId: 'FotosCavet00007' },
  { cardId: '09FC01', photoId: 'FotosCavet00001' },
  { cardId: '10FC20', photoId: 'FotosCavet00020' },
  { cardId: '11FC43', photoId: 'FotosCavet00043' },
  { cardId: '12FC45', photoId: 'FotosCavet00045' },
  { cardId: '13FC03', photoId: 'FotosCavet00003' },
  { cardId: '14FC30', photoId: 'FotosCavet00030' },
  { cardId: '15FC34', photoId: 'FotosCavet00034' }
];

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);

    const result = saveCard({
      cardId: data.id || data.cardId,
      commonName: data.commonName || "",
      scientificName: data.scientificName || "",
      comment: data.comment || "",
      fotoAuthor: data.fotoAuthor || "",
      cardAuthor: data.cardAuthor || "",
      username: data.username || data.cardAuthor || ""
    });

    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  const action = e.parameter.action;

  if (action === 'login') {
    return authenticateUser(e.parameter.username, e.parameter.password);
  }

  if (action === 'testUsers') {
    return testUsersSheet();
  }

  if (action === 'getCards') {
    return getAllCards();
  }

  if (action === 'getCard') {
    return getCard(e.parameter.cardId);
  }

  if (action === 'saveCard') {
    return saveCardFromGet(e.parameter);
  }

  if (action === 'unadoptCard') {
    return unadoptCardFromGet(e.parameter);
  }

  if (action === 'setupCardsSheet') {
    return setupCardsSheet();
  }

  return ContentService.createTextOutput("Google Sheet integration is ready.");
}

function testUsersSheet() {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Users");

    if (!sheet) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Users sheet not found. Please create a sheet named 'Users'."
      })).setMimeType(ContentService.MimeType.JSON);
    }

    const data = sheet.getDataRange().getValues();
    const headers = data[0];
    const userCount = data.length - 1;

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Users sheet found!",
      sheetName: sheet.getName(),
      headers: headers,
      userCount: userCount,
      sampleUsers: data.slice(1, 4).map(row => row[1])
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// Columns: A=Name, B=Username, C=Password, D=DisplayName, E=AdoptedCard
function authenticateUser(username, password) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Users");

  if (!sheet) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: "Users sheet not found"
    })).setMimeType(ContentService.MimeType.JSON);
  }

  const data = sheet.getDataRange().getValues();

  for (let i = 1; i < data.length; i++) {
    if (data[i][1] === username && data[i][2] === password) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        user: {
          name: data[i][0] || "",
          username: data[i][1],
          displayName: data[i][3] || data[i][0] || username,
          adoptedCard: data[i][4] || ""
        }
      })).setMimeType(ContentService.MimeType.JSON);
    }
  }

  return ContentService.createTextOutput(JSON.stringify({
    status: "error",
    message: "Invalid credentials"
  })).setMimeType(ContentService.MimeType.JSON);
}

// ==================== CARDS MANAGEMENT ====================

// Setup Cards sheet with headers and pre-populated card rows
function setupCardsSheet() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName("Cards");

    if (!sheet) {
      sheet = ss.insertSheet("Cards");
    }

    const headers = [
      "Card ID",
      "Photo ID",
      "Common Name",
      "Scientific Name",
      "Comment",
      "Foto Author",
      "Card Author",
      "Last Modified"
    ];

    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

    // Format header row
    const headerRange = sheet.getRange(1, 1, 1, headers.length);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#667eea");
    headerRange.setFontColor("#ffffff");

    // Pre-populate with 15 card rows
    CARD_SEED_DATA.forEach(function(card, idx) {
      sheet.getRange(idx + 2, 1, 1, headers.length).setValues([[
        card.cardId,
        card.photoId,
        "", // Common Name
        "", // Scientific Name
        "", // Comment
        "", // Foto Author
        "", // Card Author (empty = not adopted)
        ""  // Last Modified
      ]]);
    });

    // Auto-resize columns
    for (let i = 1; i <= headers.length; i++) {
      sheet.autoResizeColumn(i);
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: "Cards sheet created with " + CARD_SEED_DATA.length + " pre-populated cards",
      headers: headers
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// Save card data (with adoption logic)
// Cards sheet columns: A=CardID, B=PhotoID, C=CommonName, D=ScientificName, E=Comment, F=FotoAuthor, G=CardAuthor, H=LastModified
function saveCard(cardData) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const cardsSheet = ss.getSheetByName("Cards");

    if (!cardsSheet) {
      return { status: "error", message: "Cards sheet not found. Please run setupCardsSheet first." };
    }

    const data = cardsSheet.getDataRange().getValues();
    let rowIndex = -1;

    // Find existing card row (cards are pre-populated, never create new rows)
    for (let i = 1; i < data.length; i++) {
      if (data[i][0] === cardData.cardId) {
        rowIndex = i + 1; // 1-based sheet row

        // Authorization: reject if card adopted by a different user
        var existingAuthor = data[i][6]; // Column G = Card Author
        if (existingAuthor && existingAuthor !== cardData.cardAuthor && existingAuthor !== cardData.username) {
          return {
            status: "error",
            message: "Aquesta fitxa ja ha estat adoptada per " + existingAuthor
          };
        }
        break;
      }
    }

    if (rowIndex === -1) {
      return { status: "error", message: "Fitxa no trobada: " + cardData.cardId };
    }

    var isNewAdoption = !data[rowIndex - 1][6]; // Column G was empty

    // If adopting, check user doesn't already have an adopted card
    if (isNewAdoption && cardData.cardAuthor) {
      var usersSheet = ss.getSheetByName("Users");
      if (usersSheet) {
        var usersData = usersSheet.getDataRange().getValues();
        for (var j = 1; j < usersData.length; j++) {
          if (usersData[j][1] === cardData.username && usersData[j][4]) {
            return {
              status: "error",
              message: "Ja tens una fitxa adoptada: " + usersData[j][4] + ". Allibera-la primer."
            };
          }
        }
      }
    }

    // Write only allowed fields: Common Name (C), Comment (E), Card Author (G).
    // Preserve all other columns (PhotoID, ScientificName, FotoAuthor, LastModified).
    var existingRow = data[rowIndex - 1];
    var newCommonName = (typeof cardData.commonName !== 'undefined') ? cardData.commonName : existingRow[2];
    var newComment = (typeof cardData.comment !== 'undefined') ? cardData.comment : existingRow[4];
    var newCardAuthor = (typeof cardData.cardAuthor !== 'undefined') ? cardData.cardAuthor : existingRow[6];

    cardsSheet.getRange(rowIndex, 3).setValue(newCommonName); // Column C = Common Name
    cardsSheet.getRange(rowIndex, 5).setValue(newComment);    // Column E = Comment
    cardsSheet.getRange(rowIndex, 7).setValue(newCardAuthor); // Column G = Card Author
    cardsSheet.getRange(rowIndex, 8).setValue(new Date().toISOString()); // Column H = Last Modified

    // If new adoption, update the Users sheet
    if (isNewAdoption && cardData.username) {
      updateUserAdoptedCard(cardData.username, cardData.cardId);
    }

    return {
      status: "success",
      message: isNewAdoption ? "Fitxa adoptada correctament" : "Fitxa guardada correctament",
      cardId: cardData.cardId,
      adopted: isNewAdoption
    };

  } catch (error) {
    return { status: "error", message: error.toString() };
  }
}

// Wrapper for GET-based saveCard calls
function saveCardFromGet(params) {
  var result = saveCard({
    cardId: params.cardId,
    commonName: params.commonName || "",
    scientificName: params.scientificName || "",
    comment: params.comment || "",
    fotoAuthor: params.fotoAuthor || "",
    cardAuthor: params.cardAuthor || "",
    username: params.username || params.cardAuthor || ""
  });
  return ContentService.createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

// Unadopt a card: clear card data and user's adoptedCard
function unadoptCard(cardId, username) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var cardsSheet = ss.getSheetByName("Cards");

    if (!cardsSheet) {
      return { status: "error", message: "Cards sheet not found" };
    }

    var data = cardsSheet.getDataRange().getValues();
    var rowIndex = -1;

    // Resolve username to displayName for comparison with stored cardAuthor
    var usersSheet = ss.getSheetByName("Users");
    var userDisplayName = username;
    if (usersSheet) {
      var usersData = usersSheet.getDataRange().getValues();
      for (var j = 1; j < usersData.length; j++) {
        if (usersData[j][1] === username) {
          userDisplayName = usersData[j][3] || usersData[j][0] || username;
          break;
        }
      }
    }

    for (var i = 1; i < data.length; i++) {
      if (data[i][0] === cardId) {
        rowIndex = i + 1;

        // Only the card's author can unadopt
        var existingAuthor = data[i][6];
        if (existingAuthor !== userDisplayName && existingAuthor !== username) {
          return {
            status: "error",
            message: "Només l'autor de la fitxa pot alliberar-la"
          };
        }
        break;
      }
    }

    if (rowIndex === -1) {
      return { status: "error", message: "Fitxa no trobada: " + cardId };
    }

    // Clear only Common Name (C), Comment (E) and Card Author (G) to allow re-adoption.
    cardsSheet.getRange(rowIndex, 3).setValue(""); // Column C = Common Name
    cardsSheet.getRange(rowIndex, 5).setValue(""); // Column E = Comment
    cardsSheet.getRange(rowIndex, 7).setValue(""); // Column G = Card Author

    // Clear user's adoptedCard in Users sheet
    updateUserAdoptedCard(username, "");

    return {
      status: "success",
      message: "Fitxa alliberada correctament",
      cardId: cardId
    };

  } catch (error) {
    return { status: "error", message: error.toString() };
  }
}

// Wrapper for GET-based unadoptCard calls
function unadoptCardFromGet(params) {
  var result = unadoptCard(params.cardId, params.username);
  return ContentService.createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

// Update a user's AdoptedCard column (E) in the Users sheet
function updateUserAdoptedCard(username, cardId) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Users");
  if (!sheet) return;

  var data = sheet.getDataRange().getValues();
  for (var i = 1; i < data.length; i++) {
    if (data[i][1] === username) {
      sheet.getRange(i + 1, 5).setValue(cardId); // Column E = AdoptedCard
      break;
    }
  }
}

// Get all cards
// Cards sheet columns: A=CardID, B=PhotoID, C=CommonName, D=ScientificName, E=Comment, F=FotoAuthor, G=CardAuthor, H=LastModified
function getAllCards() {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Cards");

    if (!sheet) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Cards sheet not found"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var data = sheet.getDataRange().getValues();
    var cards = [];

    for (var i = 1; i < data.length; i++) {
      cards.push({
        cardId: data[i][0],
        photoId: data[i][1],
        commonName: data[i][2],
        scientificName: data[i][3],
        comment: data[i][4],
        fotoAuthor: data[i][5],
        cardAuthor: data[i][6],
        lastModified: data[i][7]
      });
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      cards: cards,
      count: cards.length
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// Get specific card
function getCard(cardId) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Cards");

    if (!sheet) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Cards sheet not found"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var data = sheet.getDataRange().getValues();

    for (var i = 1; i < data.length; i++) {
      if (data[i][0] === cardId) {
        return ContentService.createTextOutput(JSON.stringify({
          status: "success",
          card: {
            cardId: data[i][0],
            photoId: data[i][1],
            commonName: data[i][2],
            scientificName: data[i][3],
            comment: data[i][4],
            fotoAuthor: data[i][5],
            cardAuthor: data[i][6],
            lastModified: data[i][7]
          }
        })).setMimeType(ContentService.MimeType.JSON);
      }
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: "Card not found"
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
