import React, { useState } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const TrendsDashboard = () => {
  // Sample data for emotions throughout session
  const [emotionData] = useState([
    { emotion: '😊 Happy', count: 12 },
    { emotion: '😌 Calm', count: 18 },
    { emotion: '🤔 Focused', count: 25 },
    { emotion: '😰 Stressed', count: 8 },
    { emotion: '😴 Tired', count: 5 },
    { emotion: '🎉 Excited', count: 10 }
  ]);

  // Sample data for distractions per session
  const [distractionData] = useState([
    { session: 'Session 1', distractions: 5 },
    { session: 'Session 2', distractions: 3 },
    { session: 'Session 3', distractions: 7 },
    { session: 'Session 4', distractions: 2 },
    { session: 'Session 5', distractions: 4 },
    { session: 'Session 6', distractions: 1 },
    { session: 'Session 7', distractions: 6 }
  ]);

  // Most common emotion
  const mostCommonEmotion = emotionData.reduce((prev, current) => 
    (prev.count > current.count) ? prev : current
  );

  const emotionColors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  return (
    <div style={{
      fontFamily: "'Comic Sans MS', 'Chalkboard SE', 'Arial Rounded MT Bold', cursive",
      background: 'linear-gradient(135deg, #a7f3d0 0%, #6ee7b7 50%, #34d399 100%)',
      minHeight: '100vh',
      padding: '40px 20px',
      position: 'relative'
    }}>
      {/* Sparkles */}
      <div style={{
        position: 'absolute',
        fontSize: '40px',
        top: '10%',
        left: '15%',
        animation: 'sparkle 3s ease-in-out infinite'
      }}>✨</div>
      <div style={{
        position: 'absolute',
        fontSize: '35px',
        top: '20%',
        right: '15%',
        animation: 'sparkle 2.5s ease-in-out infinite'
      }}>⭐</div>
      <div style={{
        position: 'absolute',
        fontSize: '25px',
        bottom: '15%',
        left: '20%',
        animation: 'sparkle 2s ease-in-out infinite'
      }}>💫</div>

      <div style={{
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        {/* Header */}
        <div style={{
          background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
          border: '5px solid #f59e0b',
          borderRadius: '30px',
          boxShadow: '0 10px 40px rgba(245, 158, 11, 0.3), inset 0 2px 10px rgba(255, 255, 255, 0.5)',
          padding: '40px',
          marginBottom: '30px',
          textAlign: 'center'
        }}>
          <h1 style={{
            color: '#b45309',
            fontSize: '2.8em',
            textShadow: '3px 3px 0px #fbbf24',
            letterSpacing: '2px',
            margin: '0 0 10px 0'
          }}>📊 Potion Trends Laboratory 📊</h1>
          <p style={{
            color: '#d97706',
            fontStyle: 'italic',
            fontSize: '1.1em',
            margin: 0
          }}>~ Track Your Magical Progress ~</p>
        </div>

        {/* Most Common Emotion Card */}
        <div style={{
          background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
          border: '5px solid #f59e0b',
          borderRadius: '30px',
          boxShadow: '0 10px 40px rgba(245, 158, 11, 0.3)',
          padding: '40px',
          marginBottom: '30px',
          textAlign: 'center'
        }}>
          <h2 style={{
            color: '#b45309',
            fontSize: '1.8em',
            marginBottom: '20px',
            textShadow: '2px 2px 0px #fbbf24'
          }}>🏆 Most Common Emotion</h2>
          <div style={{
            fontSize: '5em',
            marginBottom: '15px'
          }}>{mostCommonEmotion.emotion.split(' ')[0]}</div>
          <div style={{
            fontSize: '2em',
            color: '#d97706',
            fontWeight: 'bold',
            marginBottom: '10px'
          }}>{mostCommonEmotion.emotion.split(' ')[1]}</div>
          <div style={{
            fontSize: '1.5em',
            color: '#78350f',
            fontWeight: 'bold'
          }}>Felt {mostCommonEmotion.count} times this session! 🎉</div>
        </div>

        {/* Charts Container */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))',
          gap: '30px',
          marginBottom: '30px'
        }}>
          {/* Emotions Bar Chart */}
          <div style={{
            background: 'linear-gradient(135deg, #ffffff 0%, #fef9e7 100%)',
            border: '5px solid #10b981',
            borderRadius: '25px',
            boxShadow: '0 8px 25px rgba(16, 185, 129, 0.3)',
            padding: '30px'
          }}>
            <h2 style={{
              color: '#047857',
              fontSize: '1.8em',
              marginBottom: '20px',
              textAlign: 'center',
              textShadow: '2px 2px 0px rgba(16, 185, 129, 0.2)'
            }}>🎭 Emotion Potion Tracker</h2>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={emotionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#d1fae5" />
                <XAxis 
                  dataKey="emotion" 
                  tick={{ fill: '#047857', fontFamily: 'Comic Sans MS', fontSize: 12 }}
                  angle={-15}
                  textAnchor="end"
                  height={80}
                />
                <YAxis 
                  tick={{ fill: '#047857', fontFamily: 'Comic Sans MS', fontSize: 14 }}
                  label={{ value: 'Times Felt', angle: -90, position: 'insideLeft', fill: '#047857', fontFamily: 'Comic Sans MS', fontWeight: 'bold' }}
                />
                <Tooltip 
                  contentStyle={{ 
                    background: '#fef3c7', 
                    border: '3px solid #f59e0b', 
                    borderRadius: '15px',
                    fontFamily: 'Comic Sans MS',
                    fontWeight: 'bold'
                  }}
                />
                <Bar dataKey="count" radius={[15, 15, 0, 0]}>
                  {emotionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={emotionColors[index % emotionColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Distractions Line Chart */}
          <div style={{
            background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
            border: '5px solid #3b82f6',
            borderRadius: '25px',
            boxShadow: '0 8px 25px rgba(59, 130, 246, 0.3)',
            padding: '30px'
          }}>
            <h2 style={{
              color: '#1e40af',
              fontSize: '1.8em',
              marginBottom: '20px',
              textAlign: 'center',
              textShadow: '2px 2px 0px rgba(59, 130, 246, 0.2)'
            }}>⚠️ Distraction Dragon Tracker</h2>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={distractionData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#bfdbfe" />
                <XAxis 
                  dataKey="session" 
                  tick={{ fill: '#1e40af', fontFamily: 'Comic Sans MS', fontSize: 12 }}
                  angle={-15}
                  textAnchor="end"
                  height={60}
                />
                <YAxis 
                  tick={{ fill: '#1e40af', fontFamily: 'Comic Sans MS', fontSize: 14 }}
                  label={{ value: '# of Distractions', angle: -90, position: 'insideLeft', fill: '#1e40af', fontFamily: 'Comic Sans MS', fontWeight: 'bold' }}
                />
                <Tooltip 
                  contentStyle={{ 
                    background: '#fef3c7', 
                    border: '3px solid #f59e0b', 
                    borderRadius: '15px',
                    fontFamily: 'Comic Sans MS',
                    fontWeight: 'bold'
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="distractions" 
                  stroke="#3b82f6" 
                  strokeWidth={4}
                  dot={{ fill: '#1e40af', r: 6 }}
                  activeDot={{ r: 8 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Stats Summary */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '20px'
        }}>
          <div style={{
            background: 'linear-gradient(135deg, #ffffff 0%, #fef9e7 100%)',
            border: '4px solid #10b981',
            borderRadius: '20px',
            padding: '25px',
            textAlign: 'center',
            boxShadow: '0 4px 10px rgba(16, 185, 129, 0.2)'
          }}>
            <div style={{ fontSize: '3em', marginBottom: '10px' }}>📈</div>
            <div style={{ fontSize: '2em', color: '#047857', fontWeight: 'bold' }}>
              {emotionData.reduce((sum, e) => sum + e.count, 0)}
            </div>
            <div style={{ color: '#059669', fontSize: '1.1em', fontWeight: 'bold' }}>Total Emotions Tracked</div>
          </div>

          <div style={{
            background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
            border: '4px solid #3b82f6',
            borderRadius: '20px',
            padding: '25px',
            textAlign: 'center',
            boxShadow: '0 4px 10px rgba(59, 130, 246, 0.2)'
          }}>
            <div style={{ fontSize: '3em', marginBottom: '10px' }}>🎯</div>
            <div style={{ fontSize: '2em', color: '#1e40af', fontWeight: 'bold' }}>
              {(distractionData.reduce((sum, d) => sum + d.distractions, 0) / distractionData.length).toFixed(1)}
            </div>
            <div style={{ color: '#2563eb', fontSize: '1.1em', fontWeight: 'bold' }}>Avg Distractions/Session</div>
          </div>

          <div style={{
            background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
            border: '4px solid #f59e0b',
            borderRadius: '20px',
            padding: '25px',
            textAlign: 'center',
            boxShadow: '0 4px 10px rgba(245, 158, 11, 0.2)'
          }}>
            <div style={{ fontSize: '3em', marginBottom: '10px' }}>🔥</div>
            <div style={{ fontSize: '2em', color: '#b45309', fontWeight: 'bold' }}>
              {distractionData.length}
            </div>
            <div style={{ color: '#d97706', fontSize: '1.1em', fontWeight: 'bold' }}>Total Sessions</div>
          </div>

          <div style={{
            background: 'linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%)',
            border: '4px solid #ec4899',
            borderRadius: '20px',
            padding: '25px',
            textAlign: 'center',
            boxShadow: '0 4px 10px rgba(236, 72, 153, 0.2)'
          }}>
            <div style={{ fontSize: '3em', marginBottom: '10px' }}>⭐</div>
            <div style={{ fontSize: '2em', color: '#be185d', fontWeight: 'bold' }}>
              {Math.min(...distractionData.map(d => d.distractions))}
            </div>
            <div style={{ color: '#db2777', fontSize: '1.1em', fontWeight: 'bold' }}>Best Focus Session!</div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes sparkle {
          0%, 100% { opacity: 0.3; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.2); }
        }
      `}</style>
    </div>
  );
};

export default TrendsDashboard;